# Peblo TV Mini 📺

Hey! Welcome to my submission for the Peblo TV Mini take-home challenge. 

Building this was a really fun (and occasionally frustrating!) journey. I spent about 9 hours in total putting this together. The goal was to build an internal CMS for content editors, a robust FastAPI backend to process and publish that content, and a Netflix-style viewer UI to consume the final published catalogue.

Here's a deep dive into how I built it, the problems I ran into, and the design decisions I made along the way.

---

## 🏗️ The Architecture

I went with a modern, fully-typed stack:
- **Backend:** FastAPI, PostgreSQL (via asyncpg), SQLAlchemy 2.0, and Alembic for migrations.
- **CMS & Viewer UIs:** React, Vite, TypeScript, and TanStack Query.
- **Storage:** A swappable storage abstraction. Right now it saves to a local disk folder (`/storage`), but it's designed to swap to S3/Cloudflare R2 with just an environment variable change.
- **Infrastructure:** Docker & Docker Compose to spin everything up at once.

## 🚀 How to Run It

1. First, set up your environment variables by copying the example file:
   ```bash
   cp .env.example .env
   ```

2. Spin up the whole stack using Docker Compose:
   ```bash
   docker compose up --build
   ```

   *Note: I originally ran into a huge headache here where my local `npm run dev` servers were conflicting with Docker's port bindings (the dreaded `bind: Only one usage of each socket address` error), and then a weird issue where my local Python 3.10 `venv` got copied into the Python 3.12 Docker container, breaking SQLAlchemy. I fixed this by adding a proper `.dockerignore` file!*

3. Once it's running, you can access the apps:
   - **CMS:** `http://localhost:5173`
   - **Viewer:** `http://localhost:5174`
   - **API Swagger Docs:** `http://localhost:8000/docs`

4. **Log in to the CMS:**
   - **Editor:** `editor` / `editor123` (Can manage content, but the publish button is locked)
   - **Admin:** `admin` / `admin123` (Has the keys to the castle — can publish!)

## 🧠 Trade-offs, Decisions, and The "Why" (Part E)

This section covers the core architectural questions from the prompt.

### 1. The Atomic Publish Pipeline 💥
One of the most interesting parts of this challenge was figuring out how to safely publish the catalogue without viewers ever seeing a broken or half-written file. 

**My Strategy:** The publish job builds the entire JSON catalogue in memory. It then writes it to a **brand new, timestamped file** (e.g., `catalogue-171542.json`). Only after that write is 100% successful does it atomically swap a pointer (`current-pointer.json`) to point to the new file, and copy it to the well-known `catalogue.json` path.

**What happens if it crashes?**
- If the backend dies *while* writing the new file, nobody cares. The Viewer is still reading the old file.
- If it dies right after the pointer swap but before returning a 200 OK to the CMS, the new catalogue is already safely live! 
- A viewer will **never** see a partially written catalogue.

### 2. Why a Static File Instead of Querying the DB?
I deliberately chose to have the Viewer UI fetch a static `catalogue.json` file rather than hitting a `/viewer/shows` API endpoint that queries PostgreSQL. 

**Why?** 
1. **Speed & Scale:** Reading a static JSON file from a CDN (like Cloudflare R2) is infinitely faster and cheaper than running complex SQL JOINs for every single viewer. 
2. **Safety:** The Viewer UI doesn't need to talk to the database at all. If the DB goes down, the Viewer stays up!
3. **Editorial Intent:** A catalogue is a point-in-time snapshot. Content editors want to preview changes in the CMS and then intentionally push them live. 

The trade-off is that edits aren't "real-time." If you fix a typo in the CMS, you have to click "Publish" for the Viewer to see it. For a streaming app, this is exactly what you want.

### 3. Scaling Search
Right now, the CMS search uses a standard PostgreSQL `ILIKE` query across joined tables. It works great for our seed data, and it's perfectly fine up to about 100,000 rows.

**When it breaks and how I'd fix it:**
If Peblo TV grows to a massive scale, `ILIKE` will become a massive bottleneck (it requires full table scans). My next step would be to add the `pg_trgm` extension for fast, typo-tolerant GIN indexing. If we hit millions of records, I'd rip database search out entirely and sync the catalogue to **Elasticsearch** or **Meilisearch** for sub-10ms response times.

### 4. Storage Abstraction (Moving to Cloudflare R2)
I built a `StorageBackend` base class with `put()`, `get()`, and `url()` methods. Right now, the app injects a `LocalStorageBackend`. 

To switch to R2, I'd just write an `R2StorageBackend` that uses `boto3` (since R2 is S3-compatible). Because of the abstraction, I wouldn't have to change a single line of application logic — just flip the `STORAGE_BACKEND=r2` environment variable.

### 5. Managing Secrets
I committed `.env.example` to show what variables are needed, but in a real production environment, **I would never use `.env` files for secrets.** 

Instead, I'd use AWS Secrets Manager or HashiCorp Vault. The CI/CD pipeline or container orchestrator (like ECS or Kubernetes) would inject those secrets as environment variables at runtime. Database passwords and JWT signing keys would be automatically rotated.

### 6. What I Left Out (and Why)
I had to make a few scoped cuts to finish this in a reasonable timeframe:
- **E2E Tests:** I wrote unit tests for the complex, risky logic (like JWT auth and Pillow image validation), but I skipped full Cypress/Playwright integration tests. I wanted to focus my time on getting the atomic pipeline and React UI right.
- **Per-Episode Artwork:** The spec asked for 3 sizes of artwork per show. I applied the show's thumbnail to all of its episodes globally, rather than building a schema to allow editors to upload unique thumbnails for every single episode.

## 🤖 AI Tools & The Debugging Journey

I used **Google Antigravity (Gemini)** and **Claude** as my co-pilots during this project. They were incredible for scaffolding the boilerplate (Dockerfiles, GitHub Actions, standard CRUD routers) which saved me hours of typing.

However, it wasn't smooth sailing. I spent a significant amount of time debugging real issues where the AI either got confused or the environment fought back:
- **The Windows bcrypt nightmare:** I hit a `ValueError: password exceeds maximum 72 bytes` error because `passlib` doesn't play nicely with modern `bcrypt` versions on Windows. I had to manually pin `bcrypt==3.2.2` to fix the hashing.
- **TypeScript Strictness in CI:** My local build worked, but GitHub Actions failed because Vite's `verbatimModuleSyntax` rule yelled about how `ReactNode` was being imported. I had to go back and strictly type all my TanStack Query API responses to satisfy the compiler.
- **Ruff Linting:** I had a bunch of unused imports (`pytest`, `sqlalchemy`) that broke the CI. I eventually figured out how to run `python -m ruff check --fix .` properly to clean the codebase.

## ⏱️ Time Breakdown (Total: ~9 hours)

- **Part A (Backend API, DB schema, publish pipeline):** ~3 hours
- **Part B (React CMS):** ~2 hours
- **Part C (Viewer UI):** ~1.5 hours
- **Part D (Docker, CI/CD, Infrastructure):** ~1 hour
- **Debugging the tricky stuff (TS types, Docker venv conflicts, bcrypt):** ~1 hour
- **Documentation & Written Reasoning:** ~30 minutes

Thanks for taking the time to review this! I had a blast building it.
