"""Publish and catalogue schemas."""
from datetime import datetime
from pydantic import BaseModel


class PublishRunResponse(BaseModel):
    id: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    shows_count: int | None = None
    episodes_count: int | None = None
    error_message: str | None = None
    catalogue_path: str | None = None

    model_config = {"from_attributes": True}


class PublishRequest(BaseModel):
    """Intentionally empty — publish takes no parameters."""
    pass


class ValidationIssue(BaseModel):
    show: str
    episode: str | None = None
    issue: str
    severity: str  # "error" or "warning"


class ValidationReportResponse(BaseModel):
    publishable: bool
    blocking_issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    summary: str = ""


# -- Catalogue JSON shapes --

class CatalogueEpisode(BaseModel):
    episode_number: int
    episode_title: str
    duration_seconds: int
    content_group: str
    languages: list[str]
    thumbnail_url: str | None = None


class CatalogueSeason(BaseModel):
    season_number: int
    is_trailer_season: bool = False
    episodes: list[CatalogueEpisode]


class CatalogueShow(BaseModel):
    slug: str
    title: str
    synopsis: str
    categories: list[str]
    section: str
    poster_url: str | None = None
    banner_url: str | None = None
    thumbnail_url: str | None = None
    seasons: list[CatalogueSeason]


class CatalogueSection(BaseModel):
    section: str
    shows: list[CatalogueShow]


class Catalogue(BaseModel):
    published_at: str
    run_id: str
    sections: list[CatalogueSection]
