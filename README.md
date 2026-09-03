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
   - **API (FastAPI)**: `http://localhost:8000`
   - **CMS (React)**: `http://localhost:5173`
   - **Viewer (React)**: `http://localhost:5174`

   **Note:** On the first startup, the database migrations will run automatically, and the `seed_shows.json` data will be seeded into the database. 

3. Open the **CMS** at `http://localhost:5173` and log in:
   - **Editor**: `editor` / `editor123` (Can manage content, cannot publish)
   - **Admin**: `admin` / `admin123` (Can manage content and publish)

4. Fix the data issues in the CMS, upload required artwork (you can find placeholder assets in `backend/storage/artwork` or upload your own), and click **Publish**.

5. Open the **Viewer UI** at `http://localhost:5174` to browse the published catalog.

## Trade-offs & Decisions

### 1. Atomic Publish Pipeline
**Decision:** The publish job builds the complete catalog JSON in memory, writes it to a new timestamped file (e.g., `catalogue-123.json`), and then atomically updates a pointer file (`current.json`) and copies it to a known path (`catalogue.json`). 
**Why:** This ensures that viewers never see a partially-written or corrupted JSON file. If the publish process crashes halfway, the old catalog remains safely untouched.

### 2. Search Implementation
**Decision:** PostgreSQL `ILIKE` on joined tables for the viewer search endpoint.
**Why:** It works well for small to medium catalogs (< 100,000 rows). 
**Scaling up:** For a much larger catalog or to handle typos/fuzzy matching, we would switch to PostgreSQL full-text search (`to_tsvector`) or offload search to a dedicated service like Meilisearch or Elasticsearch. 

### 3. Storage Abstraction
**Decision:** Implemented an abstract `StorageBackend` with a `LocalStorageBackend` concrete class, and a stubbed `R2StorageBackend`.
**Why:** The requirement was to save files to disk locally but be ready for Cloudflare R2 in production. With this abstraction, switching to R2 only requires setting `STORAGE_BACKEND=r2` in the environment variables and providing credentials. The core logic remains entirely untouched.

### 4. Seed Data Data Quality Issues
I identified and handled the deliberately planted issues:
1.  **Missing Artwork:** (`ep_0036`) Handled by validation blocking publish if an episode is published without all 3 artwork types.
2.  **No Section:** (`Rhyme Rangers`) Handled by validation blocking publish if a show is published without a section.
3.  **Duplicate Content Group/Language:** (`ep_0004` & `ep_9001`) Handled by a database unique constraint `UNIQUE(content_group, language)`. The seed script skips the duplicate and logs it. The validation report surfaces it.
4.  **Draft Episodes:** Correctly filtered out during the publish step. Only published episodes of published shows are included in the JSON.
5.  **Season 0 / Trailers:** Handled by marking `season_number == 0` as `is_trailer_season` in the catalog JSON, and displaying them separately in the Viewer UI.
6.  **Title Casing:** Handled via regex warnings in the validation report (flags ALL CAPS or all lowercase).

### 5. Front-End Separation
**Decision:** Separate React apps for the CMS and Viewer.
**Why:** They have entirely different audiences, security requirements, and performance profiles. The CMS is a heavy, authenticated SPA for internal users. The Viewer is a public, highly-optimized application. Serving them from the same bundle would be inefficient and insecure.

### 6. Authentication
**Decision:** Simple JWT-based auth with roles.
**Why:** Sufficient for a take-home, but in production, we would likely integrate with an Identity Provider (Okta, Auth0, Google Workspace) via OAuth2/OIDC. Role checks are strictly enforced on the backend routes (e.g., `require_admin` dependency for `/admin/catalog/publish`).

## Tests

To run the backend tests:
```bash
docker compose exec api pytest -v
```
Tests cover the critical publish logic (language grouping, atomic writes), artwork validation, auth roles, and validation report accuracy.
