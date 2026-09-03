"""Health check endpoint."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_db
from app.models.publish_run import PublishRun
from app.storage import get_storage

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Health check — reports DB connectivity, storage access, and last publish time.

    What I'd alert on:
    - Time since last successful publish > 48 hours (if daily publishes are expected).
      This catches both broken publish pipelines AND cases where the content team
      forgot to publish after changes.
    - Any publish_run with status='running' and started_at > 10 minutes ago.
      This means the process died mid-publish (zombie run).
    - Storage not accessible: the viewer can't load the catalogue.
    """
    result = {"status": "healthy", "checks": {}}

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        result["checks"]["database"] = "connected"
    except Exception as e:
        result["status"] = "unhealthy"
        result["checks"]["database"] = f"error: {str(e)}"

    # Check storage
    storage = get_storage()
    try:
        catalogue_exists = await storage.exists("catalogue/catalogue.json")
        result["checks"]["storage"] = "accessible"
        result["checks"]["catalogue_exists"] = catalogue_exists
    except Exception as e:
        result["checks"]["storage"] = f"error: {str(e)}"

    # Last successful publish
    try:
        last_run = await db.execute(
            select(PublishRun)
            .where(PublishRun.status == "success")
            .order_by(PublishRun.finished_at.desc())
            .limit(1)
        )
        run = last_run.scalar_one_or_none()
        if run:
            result["checks"]["last_publish"] = run.finished_at.isoformat() if run.finished_at else None
            # Calculate staleness
            if run.finished_at:
                hours_since = (datetime.now(timezone.utc) - run.finished_at).total_seconds() / 3600
                result["checks"]["hours_since_publish"] = round(hours_since, 1)
        else:
            result["checks"]["last_publish"] = None
    except Exception:
        pass

    # Check for zombie runs
    try:
        zombie_result = await db.execute(
            select(PublishRun)
            .where(PublishRun.status == "running")
        )
        zombies = zombie_result.scalars().all()
        if zombies:
            result["checks"]["zombie_runs"] = len(zombies)
            result["checks"]["alert"] = "Warning: publish run(s) stuck in 'running' state"
    except Exception:
        pass

    return result
