"""Show request/response schemas."""
from datetime import datetime
from pydantic import BaseModel


class ShowCreate(BaseModel):
    title: str
    slug: str
    section: str | None = None
    categories: list[str] = []
    synopsis: str = ""
    status: str = "draft"


class ShowUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    section: str | None = None
    categories: list[str] | None = None
    synopsis: str | None = None
    status: str | None = None


class ArtworkResponse(BaseModel):
    id: str
    artwork_type: str
    file_path: str
    url: str | None = None
    width: int
    height: int
    size_bytes: int

    model_config = {"from_attributes": True}


class SeasonResponse(BaseModel):
    id: str
    season_number: int

    model_config = {"from_attributes": True}


class ShowResponse(BaseModel):
    id: str
    title: str
    slug: str
    section: str | None = None
    categories: list[str] = []
    synopsis: str = ""
    status: str = "draft"
    created_at: datetime
    updated_at: datetime
    artworks: list[ArtworkResponse] = []
    seasons: list[SeasonResponse] = []
    episode_count: int = 0

    model_config = {"from_attributes": True}


class ShowListResponse(BaseModel):
    items: list[ShowResponse]
    total: int
    page: int
    page_size: int
