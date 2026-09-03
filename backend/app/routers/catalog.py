"""Catalogue router — public endpoints for the viewer UI.

The viewer ONLY calls these endpoints. It never calls /admin/* endpoints.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.storage import get_storage
from app.models.show import Show
from app.models.episode import Episode

router = APIRouter(prefix="/catalog", tags=["catalog"])

# In-memory cache for the catalogue to avoid reading from storage on every request
_catalogue_cache: dict = {"data": None, "etag": None}


@router.get("")
async def get_catalogue():
    """Serve the published catalogue JSON.

    This reads the pre-built catalogue file from storage — it does NOT
    query the database. This is deliberate: the catalogue is a point-in-time
    snapshot, and serving a static file is much faster than building it
    per request (especially at scale with denormalized/grouped data).

    Trade-off: The catalogue is stale until the next publish. For a CMS
    where publishes are intentional editorial actions, this is the right
    trade-off. It would bite you if you needed real-time updates.
    """
    storage = get_storage()

    try:
        data = await storage.get("catalogue/catalogue.json")
        catalogue = json.loads(data)
        return catalogue
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No catalogue has been published yet. An admin needs to publish first.",
        )


@router.get("/search")
async def search_catalogue(
    q: str | None = Query(None, description="Search term — matches show title, episode title, and category"),
    category: str | None = Query(None, description="Filter by category"),
    language: str | None = Query(None, description="Filter by language (en, hi)"),
    section: str | None = Query(None, description="Filter by section"),
    db: AsyncSession = Depends(get_db),
):
    """Search the catalogue with composable filters.

    Implementation: PostgreSQL ILIKE for text search, with filter composition via AND.

    At what scale does this stop working?
    - ILIKE works fine up to ~100K rows. Beyond that, we'd switch to PostgreSQL
      full-text search (tsvector/tsquery) or a dedicated search service like
      Meilisearch/Elasticsearch.

    What would we do next?
    - Add pg_trgm extension for fuzzy matching.
    - At >1M rows, offload to Meilisearch for sub-10ms search with typo tolerance.
    - Add search analytics to surface popular queries.
    """
    query = (
        select(Show)
        .options(
            selectinload(Show.episodes),
            selectinload(Show.artworks),
            selectinload(Show.seasons),
        )
        .where(Show.status == "published")
        .where(Show.section.isnot(None))
    )

    # Text search: match show title, episode title, or category
    if q:
        from sqlalchemy import String
        query = query.where(
            or_(
                Show.title.ilike(f"%{q}%"),
                Show.id.in_(
                    select(Episode.show_id)
                    .where(Episode.episode_title.ilike(f"%{q}%"))
                    .where(Episode.status == "published")
                    .distinct()
                ),
                # Category search: check if any category contains the search term
                Show.categories.cast(String).ilike(f"%{q}%"),
            )
        )

    # Filter by category
    if category:
        # JSONB array containment: categories @> '["adventure"]'
        query = query.where(Show.categories.contains([category]))

    # Filter by section
    if section:
        query = query.where(Show.section == section)

    result = await db.execute(query)
    shows = result.scalars().unique().all()

    # Build response matching catalogue format
    storage = get_storage()
    results = []
    for show in shows:
        # Filter episodes by language if specified
        published_eps = [e for e in show.episodes if e.status == "published"]
        if language:
            published_eps = [e for e in published_eps if e.language == language]
            if not published_eps:
                continue

        artwork_urls = {aw.artwork_type: storage.url(aw.file_path) for aw in show.artworks}

        results.append({
            "slug": show.slug,
            "title": show.title,
            "synopsis": show.synopsis,
            "categories": show.categories,
            "section": show.section,
            "poster_url": artwork_urls.get("poster"),
            "banner_url": artwork_urls.get("banner"),
            "thumbnail_url": artwork_urls.get("thumbnail"),
            "episode_count": len(published_eps),
            "languages": sorted(set(e.language for e in published_eps)),
        })

    return {
        "query": q,
        "filters": {"category": category, "language": language, "section": section},
        "results": results,
        "total": len(results),
    }
