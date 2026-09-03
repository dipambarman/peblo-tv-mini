"""Shows CRUD router — editor and admin access."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.show import Show
from app.models.user import User
from app.auth.dependencies import require_editor
from app.schemas.show import (
    ShowCreate, ShowUpdate, ShowResponse, ShowListResponse, ArtworkResponse, SeasonResponse,
)
from app.storage import get_storage

router = APIRouter(prefix="/admin/shows", tags=["shows"])


def _show_to_response(show: Show) -> ShowResponse:
    storage = get_storage()
    artworks = []
    for aw in show.artworks:
        artworks.append(ArtworkResponse(
            id=str(aw.id),
            artwork_type=aw.artwork_type,
            file_path=aw.file_path,
            url=storage.url(aw.file_path),
            width=aw.width,
            height=aw.height,
            size_bytes=aw.size_bytes,
        ))

    seasons = [
        SeasonResponse(id=str(s.id), season_number=s.season_number)
        for s in sorted(show.seasons, key=lambda s: s.season_number)
    ]

    return ShowResponse(
        id=str(show.id),
        title=show.title,
        slug=show.slug,
        section=show.section,
        categories=show.categories,
        synopsis=show.synopsis,
        status=show.status,
        created_at=show.created_at,
        updated_at=show.updated_at,
        artworks=artworks,
        seasons=seasons,
        episode_count=len(show.episodes) if show.episodes else 0,
    )


@router.get("", response_model=ShowListResponse)
async def list_shows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    section: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """List shows with search, filters, and pagination."""
    query = select(Show).options(
        selectinload(Show.artworks),
        selectinload(Show.seasons),
        selectinload(Show.episodes),
    )

    # Search by title
    if search:
        query = query.where(Show.title.ilike(f"%{search}%"))

    # Filter by section
    if section:
        query = query.where(Show.section == section)

    # Filter by status
    if status_filter:
        query = query.where(Show.status == status_filter)

    # Filter by language (shows that have episodes in this language)
    if language:
        from app.models.episode import Episode
        query = query.where(
            Show.id.in_(
                select(Episode.show_id).where(Episode.language == language).distinct()
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Show.title).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    shows = result.scalars().unique().all()

    return ShowListResponse(
        items=[_show_to_response(s) for s in shows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{show_id}", response_model=ShowResponse)
async def get_show(
    show_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Get a single show by ID."""
    result = await db.execute(
        select(Show)
        .options(
            selectinload(Show.artworks),
            selectinload(Show.seasons),
            selectinload(Show.episodes),
        )
        .where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found.")
    return _show_to_response(show)


@router.post("", response_model=ShowResponse, status_code=201)
async def create_show(
    body: ShowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Create a new show."""
    # Check slug uniqueness
    existing = await db.execute(select(Show).where(Show.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"A show with slug '{body.slug}' already exists.",
        )

    show = Show(**body.model_dump())
    db.add(show)
    await db.commit()
    await db.refresh(show)

    # Reload with relationships
    result = await db.execute(
        select(Show)
        .options(selectinload(Show.artworks), selectinload(Show.seasons), selectinload(Show.episodes))
        .where(Show.id == show.id)
    )
    show = result.scalar_one()
    return _show_to_response(show)


@router.patch("/{show_id}", response_model=ShowResponse)
async def update_show(
    show_id: str,
    body: ShowUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Update a show."""
    result = await db.execute(
        select(Show)
        .options(selectinload(Show.artworks), selectinload(Show.seasons), selectinload(Show.episodes))
        .where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found.")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(show, field, value)

    await db.commit()
    await db.refresh(show)

    result = await db.execute(
        select(Show)
        .options(selectinload(Show.artworks), selectinload(Show.seasons), selectinload(Show.episodes))
        .where(Show.id == show.id)
    )
    show = result.scalar_one()
    return _show_to_response(show)


@router.delete("/{show_id}", status_code=204)
async def delete_show(
    show_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Delete a show and all its seasons/episodes."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found.")
    await db.delete(show)
    await db.commit()
