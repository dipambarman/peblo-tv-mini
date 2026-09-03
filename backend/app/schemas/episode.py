"""Episode request/response schemas."""
from datetime import datetime
from pydantic import BaseModel


class EpisodeCreate(BaseModel):
    show_id: str
    season_number: int
    episode_number: int
    episode_title: str
    duration_seconds: int | None = None
    language: str = "en"
    content_group: str
    status: str = "draft"


class EpisodeUpdate(BaseModel):
    episode_number: int | None = None
    episode_title: str | None = None
    duration_seconds: int | None = None
    language: str | None = None
    content_group: str | None = None
    status: str | None = None


class EpisodeResponse(BaseModel):
    id: str
    show_id: str
    season_id: str
    episode_number: int
    episode_title: str
    duration_seconds: int | None = None
    language: str
    content_group: str
    status: str
    original_episode_id: str | None = None
    created_at: datetime
    updated_at: datetime
    show_title: str | None = None
    show_slug: str | None = None
    season_number: int | None = None

    model_config = {"from_attributes": True}


class EpisodeListResponse(BaseModel):
    items: list[EpisodeResponse]
    total: int
    page: int
    page_size: int
