# Peblo TV Mini

A miniature version of Peblo TV's streaming mode, featuring an internal CMS (React), an API (FastAPI + PostgreSQL), an atomic publish pipeline, and a viewer-facing UI (React).

## Architecture

- **Backend**: FastAPI, PostgreSQL (asyncpg), SQLAlchemy 2.0, Alembic for migrations.
- **CMS**: React, Vite, TypeScript, TanStack Query.
- **Viewer**: React, Vite, TypeScript, TanStack Query.
- **Storage**: Swappable abstraction (local disk for development, ready for R2/S3).
- **Publish Pipeline**: Atomic write-new-then-swap-pointer strategy. The Viewer UI reads a static JSON file from storage.
- **Containerization**: Docker & Docker Compose.

## How to Run Locally

1. Create the `.env` file (you can copy the example):
   ```bash
   cp .env.example .env
   ```

2. Start the services using Docker Compose:
   ```bash
   docker compose up --build
   ```

   This will start:
   - **PostgreSQL**: `localhost:5432`
   - **API (FastAPI)**: `http://localhost:8000` (Swagger: `http://localhost:8000/docs`)
   - **CMS (React)**: `http://localhost:5173`
   - **Viewer (React)**: `http://localhost:5174`

   **Note:** On the first startup, the database migrations will run automatically, and the `seed_shows.json` data will be seeded into the database. 

3. Open the **CMS** at `http://localhost:5173` and log in:
   - **Editor**: `editor` / `editor123` (Can manage content, cannot publish)
   - **Admin**: `admin` / `admin123` (Can manage content and publish)

4. Fix the data issues surfaced in the validation report, upload the required artwork from the `assets/` folder (some are deliberately invalid to test rejection), and click **Publish**.

5. Open the **Viewer UI** at `http://localhost:5174` to browse the published catalog Netflix-style.

### Running without Docker

If you prefer to run each service individually:

```bash
# Terminal 1 — Backend (requires PostgreSQL running on localhost:5432)
cd backend
python -m venv venv && .\venv\Scripts\activate  # or source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — CMS
cd cms && npm install && npm run dev

# Terminal 3 — Viewer
cd viewer && npm install && npm run dev
```

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Tests cover: JWT auth (creation, verification, invalid tokens), artwork validation (aspect ratio, file size, content types, unknown slots).

## Trade-offs & Decisions (Part E)

### 1. How Publishing Is Atomic — and What Happens If the Process Dies

**Strategy:** The publish job builds the complete catalogue JSON in memory, writes it to a **new timestamped file** (e.g., `catalogue-{run_id}.json`), then atomically updates a pointer file (`current-pointer.json`) and copies it to the well-known path (`catalogue.json`).

**What happens at each crash point:**
- **Before write:** No new file exists. The old catalogue remains live. The `PublishRun` record stays in `running` status (detectable by the health endpoint as a "zombie run").
- **After new file written, before pointer swap:** New file exists on disk but nobody reads it. Old catalogue is still live.
- **After pointer swap:** The new catalogue is live. Even if the process dies before marking the run as `success`, the catalogue is safely served.

This is a classic write-new-then-swap pattern. The key guarantee: **a viewer never sees a half-written catalogue**.

### 2. Storage Abstraction: What Changes for Cloudflare R2?

The storage layer is an abstract `StorageBackend` class with `put()`, `get()`, `delete()`, `exists()`, and `url()` methods. Currently implemented as `LocalStorageBackend` (saves to disk).

**To switch to R2:** Set `STORAGE_BACKEND=r2` in `.env` and provide credentials (`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, etc.). The `R2StorageBackend` class uses the same interface but calls R2's S3-compatible API via `boto3`. No application code changes — just one environment variable.

### 3. Search: How It Works, Scaling Limits, and What's Next

**Implementation:** PostgreSQL `ILIKE` on joined tables. `q` matches show title, episode title, and category name. Filters (`category`, `language`, `section`) compose via `AND`.

**When it stops working:** `ILIKE` scans the full column for each query. It's fine up to ~100K rows. Beyond that, it becomes slow and lacks fuzzy matching.

**What I'd do next:**
1. Add `pg_trgm` extension + GIN index for fuzzy matching (handles typos).
2. At >1M rows, offload to Meilisearch or Elasticsearch for sub-10ms search with typo tolerance and faceted filtering.
3. Add search analytics to surface popular queries and optimize auto-suggest.

### 4. Why Serve a Pre-Published Catalogue File Instead of Querying the DB?

**Why:** The catalogue is a **point-in-time snapshot** — a deliberate editorial decision. Serving a pre-built static JSON file gives us:
- **Speed:** No JOINs, no query planning, no connection pool pressure. Just read a file.
- **Consistency:** Every viewer sees exactly the same data. No race conditions between a content edit and a viewer request.
- **Simplicity:** The Viewer UI is a pure consumer of a static artifact. It doesn't need database credentials, connection strings, or write access.
- **Scalability:** The JSON file can be served from a CDN (Cloudflare R2 + Workers) with zero backend involvement.

**Where it bites you:** The catalogue is stale until the next publish. If a content editor fixes a typo and expects it to be live immediately, they'll be confused until they click Publish again. For a CMS where publishes are intentional editorial actions, this is the right trade-off. It would be wrong for a real-time collaborative editing product.

### 5. Seed Data Quality Issues Found

The seed data contains **deliberate errors** which my validation report surfaces:

| Issue | How It's Handled |
|-------|-----------------|
| Duplicate `(content_group, language)` pair — `ep_9001` duplicates `ep_0004` | Skipped during seed with a logged warning. Surfaced in validation report. |
| Published show without a section (`Rhyme Rangers`) | Validation report blocks publish. Show excluded from catalogue. |
| Missing artwork on published episodes | Validation report flags as blocking error. |
| Draft episodes mixed with published | Filtered out during catalogue build — only published episodes of published shows appear. |
| Season 0 (trailers) | Marked as `is_trailer_season` in catalogue. Viewer shows as "Trailers & Extras" tab. |
| Title casing anomalies (ALL CAPS / all lowercase) | Validation report warns (non-blocking). |
| Invalid language codes | Validation report warns. |

### 6. What I Left Out and Why

- **End-to-end / integration tests:** I wrote unit tests for the riskiest pure-logic components (auth, image validation). Full integration tests with a test database would add confidence but take significantly more time. Given the time constraint, I prioritised demonstrating that the architecture is testable over maximising coverage.
- **Episode-level artwork:** The spec says "three sizes per show." I implemented artwork at the show level (poster/banner/thumbnail per show), not per-episode. The `thumbnail_url` in the catalogue is the show's thumbnail applied to all episodes. A per-episode artwork system would require a different schema.
- **Real CD target:** The deploy step in CI is a dry-run. In production I'd push images to ECR/GCR, run `alembic upgrade head` via a migration job, and do a canary deploy with health-check gating.
- **Pagination in Viewer:** The viewer currently loads the full catalogue JSON. For a production catalogue with thousands of shows, I'd paginate the API response or implement virtual scrolling.

### 7. AI Tools Used

I used **Google Antigravity (Gemini)** as a coding assistant throughout this project. It helped with:
- Scaffolding boilerplate (Dockerfiles, CI config, initial model definitions).
- Generating repetitive CRUD endpoints and React component structure.
- Debugging runtime issues (bcrypt/passlib version incompatibility, TypeScript strict mode errors).

I reviewed and edited all generated code. Key places where I rejected or significantly modified AI suggestions:
- The publish pipeline's atomic write strategy was my own design — the AI initially suggested a simple overwrite.
- The validation service's business rules were hand-written based on reading the seed data and reference.json.
- Storage abstraction interface design was my decision (the AI suggested a simpler approach without `url()` and `exists()` methods).

### 8. Managing Secrets in Production

The `.env.example` file documents every variable the system needs. In production, I would **never** store secrets in `.env` files or commit them to Git. Instead:

- **Database credentials & JWT secrets:** Stored in a secrets manager (AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault). Injected as environment variables at deploy time by the CI/CD pipeline or the container orchestrator (ECS task definition / Kubernetes secrets).
- **R2/S3 credentials:** Use IAM roles (AWS) or Workload Identity (GCP) to eliminate static credentials entirely. The container assumes a role that has the necessary permissions.
- **Rotation:** JWT secrets and database passwords should be rotated on a schedule. The secrets manager handles rotation; the application reads fresh values on restart.
- **Local development:** Developers use `.env` files with development-only credentials that have no access to production data.

### 9. What I'd Alert On

The `/health` endpoint checks three things, and I'd alert on:

1. **Time since last successful publish > 48 hours.** If daily publishes are expected, this catches both broken pipelines and human error (forgetting to publish).
2. **Zombie publish runs** — any `PublishRun` with `status='running'` and `started_at` > 10 minutes ago. This means the process died mid-publish and needs manual intervention.
3. **Storage not accessible.** If the catalogue file can't be read, the viewer is broken.

## Time Spent

| Part | Approx Time |
|------|-------------|
| Part A — Backend (API, models, publish, validation) | ~3 hours |
| Part B — CMS (React) | ~2 hours |
| Part C — Viewer UI (React) | ~1.5 hours |
| Part D — Pipeline (Docker, CI, .env) | ~1 hour |
| Part E — Written reasoning | ~30 minutes |
| Debugging & polish (bcrypt, TS strict, lint fixes) | ~1 hour |
| **Total** | **~9 hours** |
