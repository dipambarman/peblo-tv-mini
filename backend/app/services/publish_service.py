"""Publish service — atomic catalogue build with content_group language collapsing."""
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.show import Show
from app.models.episode import Episode
from app.models.publish_run import PublishRun
from app.models.user import User
from app.storage import get_storage
from app.schemas.publish import (
    Catalogue, CatalogueSection, CatalogueShow,
    CatalogueSeason, CatalogueEpisode,
)

logger = logging.getLogger(__name__)

# Section display order from reference.json
SECTION_ORDER = ["featured", "series", "minisodes", "songs"]


async def publish_catalogue(db: AsyncSession, user: User) -> PublishRun:
    """Build and atomically publish the catalogue JSON.

    Strategy:
    1. Create a PublishRun record with status='running'.
    2. Build the catalogue JSON in memory.
    3. Write to a NEW timestamped key (never overwrites the live file directly).
    4. Update the 'current' pointer to the new file.
    5. Mark the run as 'success'.

    If the process dies at any point:
    - Steps 1-2: No catalogue written, old one still live. Run marked 'running' (detectable).
    - Step 3: New file written but not pointed to. Old one still live.
    - Step 4: Atomic pointer update. Either the old or new pointer is live.
    - Step 5: Catalogue is live even if this fails (run just shows 'running').
    """
    storage = get_storage()

    # Step 1: Create the run record
    run = PublishRun(
        triggered_by=user.id,
        status="running",
    )
    db.add(run)
    await db.flush()  # Get the run ID

    try:
        # Step 2: Build the catalogue
        catalogue = await _build_catalogue(db, str(run.id))

        catalogue_json = catalogue.model_dump_json(indent=2)
        catalogue_bytes = catalogue_json.encode("utf-8")

        # Count for the run record
        total_shows = sum(len(section.shows) for section in catalogue.sections)
        total_episodes = sum(
            sum(len(season.episodes) for season in show.seasons)
            for section in catalogue.sections
            for show in section.shows
        )

        # Step 3: Write to a NEW key (never overwrite the live file)
        run_key = f"catalogue/catalogue-{run.id}.json"
        await storage.put(run_key, catalogue_bytes, content_type="application/json")

        # Step 4: Atomically update the 'current' pointer
        # On local disk: write a small pointer file
        # On R2: overwrite the pointer key (atomic single-object PUT)
        pointer_data = json.dumps({"current": run_key, "run_id": str(run.id)}).encode()
        await storage.put("catalogue/current-pointer.json", pointer_data, "application/json")

        # Also write the catalogue to a well-known path for easy GET /catalog serving
        await storage.put("catalogue/catalogue.json", catalogue_bytes, "application/json")

        # Step 5: Mark success
        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        run.shows_count = total_shows
        run.episodes_count = total_episodes
        run.catalogue_path = run_key

        await db.commit()

        logger.info(
            f"Catalogue published: {total_shows} shows, {total_episodes} episodes. "
            f"Run ID: {run.id}"
        )
        return run

    except Exception as e:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = str(e)
        await db.commit()
        logger.error(f"Publish failed: {e}")
        raise


async def _build_catalogue(db: AsyncSession, run_id: str) -> Catalogue:
    """Build the catalogue JSON structure from published data.

    Key rules:
    - Only published shows with published episodes appear.
    - Published shows must have a section.
    - content_group variants collapse into ONE entry with a languages list.
    - Season 0 is marked as trailer season.
    - Grouped by section, deterministic ordering (section order, then show title, then season, then episode).
    """
    storage = get_storage()

    # Fetch all published shows with their data
    result = await db.execute(
        select(Show)
        .options(
            selectinload(Show.episodes),
            selectinload(Show.artworks),
            selectinload(Show.seasons),
        )
        .where(Show.status == "published")
        .where(Show.section.isnot(None))
    )
    shows = result.scalars().all()

    # Group shows by section
    section_shows: dict[str, list[CatalogueShow]] = defaultdict(list)

    for show in shows:
        published_episodes = [
            e for e in show.episodes if e.status == "published"
        ]

        if not published_episodes:
            continue

        # Build artwork URLs
        artwork_urls = {}
        for aw in show.artworks:
            artwork_urls[aw.artwork_type] = storage.url(aw.file_path)

        # Group episodes by season
        season_map: dict[int, list[Episode]] = defaultdict(list)
        for ep in published_episodes:
            season_num = _get_season_number(show, ep)
            season_map[season_num].append(ep)

        # Build seasons
        catalogue_seasons = []
        for season_num in sorted(season_map.keys()):
            season_episodes = season_map[season_num]
            is_trailer = season_num == 0

            # Collapse content_group variants into one entry
            content_groups: dict[str, dict] = {}
            for ep in season_episodes:
                cg = ep.content_group
                if cg not in content_groups:
                    content_groups[cg] = {
                        "episode_number": ep.episode_number,
                        "episode_title": ep.episode_title,
                        "duration_seconds": ep.duration_seconds or 0,
                        "content_group": cg,
                        "languages": [],
                        "thumbnail_url": artwork_urls.get("thumbnail"),
                    }
                # Add this language variant
                if ep.language not in content_groups[cg]["languages"]:
                    content_groups[cg]["languages"].append(ep.language)

            # Sort languages for determinism
            for cg_data in content_groups.values():
                cg_data["languages"].sort()

            # Sort episodes by episode_number for deterministic ordering
            sorted_episodes = sorted(
                content_groups.values(),
                key=lambda x: x["episode_number"],
            )

            catalogue_seasons.append(CatalogueSeason(
                season_number=season_num,
                is_trailer_season=is_trailer,
                episodes=[CatalogueEpisode(**ep) for ep in sorted_episodes],
            ))

        catalogue_show = CatalogueShow(
            slug=show.slug,
            title=show.title,
            synopsis=show.synopsis,
            categories=sorted(show.categories),
            section=show.section,
            poster_url=artwork_urls.get("poster"),
            banner_url=artwork_urls.get("banner"),
            thumbnail_url=artwork_urls.get("thumbnail"),
            seasons=catalogue_seasons,
        )
        section_shows[show.section].append(catalogue_show)

    # Sort shows within each section by title
    for section in section_shows:
        section_shows[section].sort(key=lambda s: s.title)

    # Build final catalogue with deterministic section ordering
    sections = []
    for section_name in SECTION_ORDER:
        if section_name in section_shows:
            sections.append(CatalogueSection(
                section=section_name,
                shows=section_shows[section_name],
            ))

    return Catalogue(
        published_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        sections=sections,
    )


def _get_season_number(show: Show, episode: Episode) -> int:
    """Get the season number for an episode."""
    for s in show.seasons:
        if s.id == episode.season_id:
            return s.season_number
    return 1
