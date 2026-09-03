"""Peblo TV Mini — FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, shows, episodes, artwork, publish, catalog, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — create tables and seed on startup."""
    # Import all models so they're registered with Base
    from app.models import Show, Season, Episode, Artwork, PublishRun, User  # noqa: F401

    # Create tables (for development; in production use Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data if configured
    if settings.SEED_ON_STARTUP:
        from app.services.seed_service import run_seed
        async with AsyncSessionLocal() as session:
            await run_seed(session)

    logger.info("Peblo TV Mini API started!")
    yield

    # Shutdown
    await engine.dispose()
    logger.info("Peblo TV Mini API stopped.")


app = FastAPI(
    title="Peblo TV Mini API",
    description="CMS → Published Catalogue → Viewer API for Peblo TV",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow CMS and Viewer frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file serving for local storage
storage_path = settings.STORAGE_LOCAL_PATH
if not os.path.exists(storage_path):
    os.makedirs(storage_path)

app.mount("/static/storage", StaticFiles(directory=storage_path), name="storage")

# Register routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(shows.router)
app.include_router(episodes.router)
app.include_router(artwork.router)
app.include_router(publish.router)
app.include_router(catalog.router)


@app.get("/")
async def root():
    return {
        "service": "Peblo TV Mini API",
        "docs": "/docs",
        "health": "/health",
    }
