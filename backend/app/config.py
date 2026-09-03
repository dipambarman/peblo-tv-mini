"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://peblo:peblo_secret@localhost:5432/peblo_tv"
    DATABASE_URL_SYNC: str = "postgresql://peblo:peblo_secret@localhost:5432/peblo_tv"

    # Auth
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "r2"
    STORAGE_LOCAL_PATH: str = "./storage"
    STORAGE_SERVE_URL: str = "/static/storage"

    # R2 (only if STORAGE_BACKEND=r2)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""

    # Seeding
    SEED_ON_STARTUP: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
