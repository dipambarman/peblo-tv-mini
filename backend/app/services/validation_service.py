"""Validation service — surfaces everything currently blocking publish."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.show import Show
from app.models.episode import Episode
from app.schemas.publish import ValidationIssue, ValidationReportResponse

# Valid values from reference.json
VALID_SECTIONS = {"featured", "series", "minisodes", "songs"}
VALID_CATEGORIES = {
    "adventure", "folk", "friendship", "india", "language", "learning",
    "maths", "music", "nature", "reading", "science", "singalong",
    "stories", "travel", "values",
}
VALID_LANGUAGES = {"en", "hi"}


async def build_validation_report(db: AsyncSession) -> ValidationReportResponse:
    """Build a comprehensive validation report grouped by show."""
    blocking: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # Load all shows with their episodes and artwork
    result = await db.execute(
        select(Show)
        .options(
            selectinload(Show.episodes),
            selectinload(Show.artworks),
            selectinload(Show.seasons),
        )
        .order_by(Show.title)
    )
    shows = result.scalars().all()

    for show in shows:
        published_episodes = [e for e in show.episodes if e.status == "published"]

        # Check 1: Published show must have a section
        if show.status == "published" and not show.section:
            blocking.append(ValidationIssue(
                show=show.title,
                issue=(
                    "No section assigned. A published show must belong to a section "
                    "(featured, series, minisodes, or songs)."
                ),
                severity="error",
            ))

        # Check 1b: Section must be valid
        if show.section and show.section not in VALID_SECTIONS:
            blocking.append(ValidationIssue(
                show=show.title,
                issue=(
                    f"Section '{show.section}' is not valid. "
                    f"Must be one of: {', '.join(sorted(VALID_SECTIONS))}."
                ),
                severity="error",
            ))

        # Check 2: Invalid categories
        invalid_cats = set(show.categories) - VALID_CATEGORIES
        if invalid_cats:
            warnings.append(ValidationIssue(
                show=show.title,
                issue=(
                    f"Unknown categories: {', '.join(sorted(invalid_cats))}. "
                    f"Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}."
                ),
                severity="warning",
            ))

        # Check 3: Published episodes without artwork
        artwork_types = {a.artwork_type for a in show.artworks}
        if published_episodes and len(artwork_types) < 3:
            missing = {"poster", "banner", "thumbnail"} - artwork_types
            blocking.append(ValidationIssue(
                show=show.title,
                issue=(
                    f"Missing artwork: {', '.join(sorted(missing))}. "
                    f"All three artwork types (poster, banner, thumbnail) are required "
                    f"before publishing."
                ),
                severity="error",
            ))

        # Check 4: Published episodes without duration
        for ep in published_episodes:
            if not ep.duration_seconds:
                blocking.append(ValidationIssue(
                    show=show.title,
                    episode=f"S{ep.season_id}E{ep.episode_number} — {ep.episode_title}",
                    issue=(
                        "This episode has no duration set. "
                        "An episode can't be published without a duration."
                    ),
                    severity="error",
                ))

        # Check 5: Episode title casing issues
        for ep in show.episodes:
            title = ep.episode_title
            if title == title.upper() and len(title) > 3:
                warnings.append(ValidationIssue(
                    show=show.title,
                    episode=f"S{_season_num(show, ep)}E{ep.episode_number}",
                    issue=(
                        f"Episode title '{title}' appears to be ALL CAPS. "
                        f"Did you mean '{title.title()}'?"
                    ),
                    severity="warning",
                ))
            elif title == title.lower() and len(title) > 3:
                warnings.append(ValidationIssue(
                    show=show.title,
                    episode=f"S{_season_num(show, ep)}E{ep.episode_number}",
                    issue=(
                        f"Episode title '{title}' appears to be all lowercase. "
                        f"Did you mean '{title.title()}'?"
                    ),
                    severity="warning",
                ))

        # Check 6: Invalid language
        for ep in show.episodes:
            if ep.language not in VALID_LANGUAGES:
                warnings.append(ValidationIssue(
                    show=show.title,
                    episode=f"S{_season_num(show, ep)}E{ep.episode_number}",
                    issue=(
                        f"Language '{ep.language}' is not in the allowed list: "
                        f"{', '.join(sorted(VALID_LANGUAGES))}."
                    ),
                    severity="warning",
                ))

    # Check 7: Duplicate content_group + language across ALL episodes
    # (DB constraint prevents this during seed, but report it for transparency)
    dup_result = await db.execute(
        select(
            Episode.content_group,
            Episode.language,
            func.count().label("cnt"),
        )
        .group_by(Episode.content_group, Episode.language)
        .having(func.count() > 1)
    )
    for row in dup_result.all():
        blocking.append(ValidationIssue(
            show="Multiple",
            episode=f"content_group='{row.content_group}', language='{row.language}'",
            issue=(
                f"Duplicate (content_group, language) pair found ({row.cnt} episodes). "
                f"Each content_group+language combination must be unique."
            ),
            severity="error",
        ))

    publishable = len(blocking) == 0
    summary = (
        f"{'✅ Ready to publish!' if publishable else '❌ Cannot publish.'} "
        f"{len(blocking)} blocking issue(s), {len(warnings)} warning(s)."
    )

    return ValidationReportResponse(
        publishable=publishable,
        blocking_issues=blocking,
        warnings=warnings,
        summary=summary,
    )


def _season_num(show: Show, episode: Episode) -> int:
    """Helper to get the season number for an episode."""
    for s in show.seasons:
        if s.id == episode.season_id:
            return s.season_number
    return 0
