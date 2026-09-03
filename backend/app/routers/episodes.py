"""Episodes CRUD router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.user import User
from app.auth.dependencies import require_editor
from app.schemas.episode import (
    EpisodeCreate, EpisodeUpdate, EpisodeResponse, EpisodeListResponse,
)

router = APIRouter(prefix="/admin/episodes", tags=["episodes"])


def _episode_to_response(ep: Episode, show: Show | None = None, season: Season | None = None) -> EpisodeResponse:
    return EpisodeResponse(
        id=str(ep.id),
        show_id=str(ep.show_id),
        season_id=str(ep.season_id),
        episode_number=ep.episode_number,
        episode_title=ep.episode_title,
        duration_seconds=ep.duration_seconds,
        language=ep.language,
        content_group=ep.content_group,
        status=ep.status,
        original_episode_id=ep.original_episode_id,
        created_at=ep.created_at,
        updated_at=ep.updated_at,
        show_title=show.title if show else None,
        show_slug=show.slug if show else None,
        season_number=season.season_number if season else None,
    )


@router.get("", response_model=EpisodeListResponse)
async def list_episodes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    show_id: str | None = None,
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    language: str | None = None,
    season_number: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """List episodes with filters and pagination."""
    query = (
        select(Episode)
        .join(Show, Episode.show_id == Show.id)
        .join(Season, Episode.season_id == Season.id)
    )

    if show_id:
        query = query.where(Episode.show_id == show_id)
    if search:
        query = query.where(
            (Episode.episode_title.ilike(f"%{search}%")) |
            (Show.title.ilike(f"%{search}%"))
        )
    if status_filter:
        query = query.where(Episode.status == status_filter)
    if language:
        query = query.where(Episode.language == language)
    if season_number is not None:
        query = query.where(Season.season_number == season_number)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate and fetch with joins
    query = (
        query
        .add_columns(Show, Season)
        .order_by(Show.title, Season.season_number, Episode.episode_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    items = [_episode_to_response(ep, show, season) for ep, show, season in rows]

    return EpisodeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Get a single episode."""
    result = await db.execute(
        select(Episode, Show, Season)
        .join(Show, Episode.show_id == Show.id)
        .join(Season, Episode.season_id == Season.id)
        .where(Episode.id == episode_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Episode not found.")
    ep, show, season = row
    return _episode_to_response(ep, show, season)


@router.post("", response_model=EpisodeResponse, status_code=201)
async def create_episode(
    body: EpisodeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Create a new episode."""
    # Validate show exists
    result = await db.execute(select(Show).where(Show.id == body.show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found.")

    # Get or create season
    result = await db.execute(
        select(Season).where(
            Season.show_id == body.show_id,
            Season.season_number == body.season_number,
        )
    )
    season = result.scalar_one_or_none()
    if not season:
        season = Season(show_id=show.id, season_number=body.season_number)
        db.add(season)
        await db.flush()

    # Check unique constraint before hitting DB
    existing = await db.execute(
        select(Episode).where(
            Episode.content_group == body.content_group,
            Episode.language == body.language,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=(
                f"An episode already exists with content_group='{body.content_group}' "
                f"and language='{body.language}'. Each (content_group, language) pair must be unique."
            ),
        )

    episode = Episode(
        show_id=show.id,
        season_id=season.id,
        episode_number=body.episode_number,
        episode_title=body.episode_title,
        duration_seconds=body.duration_seconds,
        language=body.language,
        content_group=body.content_group,
        status=body.status,
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)

    return _episode_to_response(episode, show, season)


@router.patch("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: str,
    body: EpisodeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Update an episode."""
    result = await db.execute(
        select(Episode, Show, Season)
        .join(Show, Episode.show_id == Show.id)
        .join(Season, Episode.season_id == Season.id)
        .where(Episode.id == episode_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Episode not found.")

    ep, show, season = row
    update_data = body.model_dump(exclude_unset=True)

    # If changing content_group or language, check uniqueness
    new_cg = update_data.get("content_group", ep.content_group)
    new_lang = update_data.get("language", ep.language)
    if new_cg != ep.content_group or new_lang != ep.language:
        existing = await db.execute(
            select(Episode).where(
                Episode.content_group == new_cg,
                Episode.language == new_lang,
                Episode.id != ep.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Another episode already exists with content_group='{new_cg}' and language='{new_lang}'.",
            )

    for field, value in update_data.items():
        setattr(ep, field, value)

    await db.commit()
    await db.refresh(ep)
    return _episode_to_response(ep, show, season)


@router.delete("/{episode_id}", status_code=204)
async def delete_episode(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Delete an episode."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found.")
    await db.delete(ep)
    await db.commit()
