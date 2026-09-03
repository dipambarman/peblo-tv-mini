"""Artwork upload router with server-side validation."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.show import Show
from app.models.artwork import Artwork
from app.models.user import User
from app.auth.dependencies import require_editor
from app.storage import get_storage
from app.utils.image_validation import validate_artwork, ARTWORK_SPECS

router = APIRouter(prefix="/admin/shows", tags=["artwork"])


@router.post("/{show_id}/artwork/{artwork_type}")
async def upload_artwork(
    show_id: str,
    artwork_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_editor),
):
    """Upload artwork for a show.

    Validates:
    - File type (JPEG, PNG, WebP)
    - Aspect ratio (within 5% tolerance)
    - File size (≤200KB)

    Returns human-readable errors that a content editor can act on.
    """
    if artwork_type not in ARTWORK_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown artwork type '{artwork_type}'. Must be one of: poster, banner, thumbnail.",
        )

    # Verify show exists
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found.")

    # Read file data
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Validate the image — this is SERVER-SIDE, not client-only
    is_valid, errors, metadata = validate_artwork(file_data, content_type, artwork_type)

    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Artwork validation failed. Please fix the issues below and try again.",
                "errors": errors,
                "specs": ARTWORK_SPECS[artwork_type],
                "uploaded": metadata,
            },
        )

    # Store the file
    storage = get_storage()
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    file_key = f"artwork/{show.slug}/{artwork_type}_{uuid.uuid4().hex[:8]}.{ext}"
    await storage.put(file_key, file_data, content_type)

    # Upsert artwork record — replace existing if present
    result = await db.execute(
        select(Artwork).where(
            Artwork.show_id == show.id,
            Artwork.artwork_type == artwork_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Delete old file from storage
        try:
            await storage.delete(existing.file_path)
        except Exception:
            pass
        existing.file_path = file_key
        existing.width = metadata["width"]
        existing.height = metadata["height"]
        existing.size_bytes = metadata["size_bytes"]
        existing.content_type = content_type
        artwork = existing
    else:
        artwork = Artwork(
            show_id=show.id,
            artwork_type=artwork_type,
            file_path=file_key,
            width=metadata["width"],
            height=metadata["height"],
            size_bytes=metadata["size_bytes"],
            content_type=content_type,
        )
        db.add(artwork)

    await db.commit()
    await db.refresh(artwork)

    return {
        "id": str(artwork.id),
        "artwork_type": artwork.artwork_type,
        "url": storage.url(artwork.file_path),
        "width": artwork.width,
        "height": artwork.height,
        "size_bytes": artwork.size_bytes,
        "message": f"✅ {artwork_type.title()} uploaded successfully!",
    }
