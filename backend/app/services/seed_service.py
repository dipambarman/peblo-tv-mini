"""Seed service — loads seed_shows.json into the database on startup."""
import json
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.auth.security import hash_password

logger = logging.getLogger(__name__)

SEED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "seed_shows.json")


async def seed_users(db: AsyncSession) -> None:
    """Create default editor and admin users if they don't exist."""
    count = await db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        logger.info("Users already seeded, skipping.")
        return

    users = [
        User(username="editor", password_hash=hash_password("editor123"), role="editor"),
        User(username="admin", password_hash=hash_password("admin123"), role="admin"),
    ]
    db.add_all(users)
    await db.commit()
    logger.info("Seeded 2 users: editor (editor), admin (admin).")


async def seed_shows(db: AsyncSession) -> None:
    """Load seed_shows.json and populate shows, seasons, episodes."""
    count = await db.scalar(select(func.count()).select_from(Show))
    if count and count > 0:
        logger.info("Shows already seeded, skipping.")
        return

    if not os.path.exists(SEED_FILE):
        logger.warning(f"Seed file not found at {SEED_FILE}, skipping seed.")
        return

    with open(SEED_FILE, "r") as f:
        episodes_data = json.load(f)

    logger.info(f"Seeding {len(episodes_data)} episodes from seed_shows.json...")

    # First pass: collect unique shows and seasons
    shows_map: dict[str, Show] = {}
    seasons_map: dict[str, Season] = {}  # key: f"{slug}:{season_number}"

    for ep_data in episodes_data:
        slug = ep_data["slug"]

        # Create show if not seen
        if slug not in shows_map:
            show = Show(
                title=ep_data["show_title"],
                slug=slug,
                section=ep_data.get("section"),
                categories=ep_data.get("categories", []),
                synopsis=ep_data.get("synopsis", ""),
                status="published" if ep_data.get("status") == "published" else "draft",
            )
            db.add(show)
            shows_map[slug] = show

        # Create season if not seen
        season_key = f"{slug}:{ep_data['season_number']}"
        if season_key not in seasons_map:
            season = Season(
                show_id=shows_map[slug].id,
                season_number=ep_data["season_number"],
            )
            # We need to set the relationship correctly
            shows_map[slug].seasons.append(season)
            seasons_map[season_key] = season

    # Flush to get IDs
    await db.flush()

    # Second pass: create episodes
    # Track content_group+language to handle the duplicate gracefully
    seen_content_lang: set[str] = set()
    skipped = 0

    for ep_data in episodes_data:
        slug = ep_data["slug"]
        season_key = f"{slug}:{ep_data['season_number']}"

        content_lang_key = f"{ep_data['content_group']}:{ep_data['language']}"

        if content_lang_key in seen_content_lang:
            # This is the deliberate duplicate — log it but skip to avoid DB constraint violation
            logger.warning(
                f"Skipping duplicate (content_group={ep_data['content_group']}, "
                f"language={ep_data['language']}) — episode_id={ep_data['episode_id']}. "
                f"This will appear in the validation report."
            )
            skipped += 1
            continue
        seen_content_lang.add(content_lang_key)

        episode = Episode(
            show_id=shows_map[slug].id,
            season_id=seasons_map[season_key].id,
            episode_number=ep_data["episode_number"],
            episode_title=ep_data["episode_title"],
            duration_seconds=ep_data.get("duration_seconds"),
            language=ep_data["language"],
            content_group=ep_data["content_group"],
            status=ep_data.get("status", "draft"),
            original_episode_id=ep_data.get("episode_id"),
        )
        db.add(episode)

    await db.commit()
    logger.info(
        f"Seeded {len(shows_map)} shows, {len(seasons_map)} seasons, "
        f"{len(episodes_data) - skipped} episodes ({skipped} skipped as duplicates)."
    )


async def run_seed(db: AsyncSession) -> None:
    """Run all seed operations."""
    await seed_users(db)
    await seed_shows(db)
