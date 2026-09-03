"""Image validation utilities for artwork uploads."""
from io import BytesIO
from PIL import Image

# Artwork specs from reference.json
ARTWORK_SPECS = {
    "poster": {
        "aspect": (2, 3),
        "target_px": (600, 900),
        "max_kb": 200,
        "description": "Poster (2:3 ratio, ~600×900px)",
    },
    "banner": {
        "aspect": (16, 9),
        "target_px": (1280, 720),
        "max_kb": 200,
        "description": "Banner (16:9 ratio, ~1280×720px)",
    },
    "thumbnail": {
        "aspect": (16, 9),
        "target_px": (640, 360),
        "max_kb": 200,
        "description": "Thumbnail (16:9 ratio, ~640×360px)",
    },
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# 5% tolerance on aspect ratio
ASPECT_TOLERANCE = 0.05


def validate_artwork(
    file_data: bytes,
    content_type: str,
    artwork_type: str,
) -> tuple[bool, list[str], dict | None]:
    """Validate an uploaded artwork image.

    Returns:
        (is_valid, errors, metadata)
        - is_valid: True if the image passes all checks.
        - errors: List of human-readable error messages (for non-technical editors).
        - metadata: dict with width, height, size_bytes if image could be read, else None.
    """
    errors: list[str] = []
    spec = ARTWORK_SPECS.get(artwork_type)

    if spec is None:
        return False, [f"Unknown artwork type '{artwork_type}'. Must be one of: poster, banner, thumbnail."], None

    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        errors.append(
            f"This file type isn't supported. Please upload a JPEG, PNG, or WebP image. "
            f"You uploaded: {content_type}"
        )
        return False, errors, None

    # Check file size
    size_bytes = len(file_data)
    max_bytes = spec["max_kb"] * 1024
    if size_bytes > max_bytes:
        size_kb = size_bytes / 1024
        errors.append(
            f"This image is {size_kb:.0f} KB, but the maximum allowed size is {spec['max_kb']} KB. "
            f"Please compress the image or reduce its resolution."
        )

    # Try to open and read dimensions
    try:
        img = Image.open(BytesIO(file_data))
        width, height = img.size
    except Exception:
        errors.append(
            "This file doesn't appear to be a valid image. "
            "Please check the file and try again."
        )
        return False, errors, None

    metadata = {
        "width": width,
        "height": height,
        "size_bytes": size_bytes,
    }

    # Check aspect ratio
    target_w, target_h = spec["aspect"]
    expected_ratio = target_w / target_h
    actual_ratio = width / height if height > 0 else 0

    if abs(actual_ratio - expected_ratio) / expected_ratio > ASPECT_TOLERANCE:
        errors.append(
            f"This image is {width}×{height} pixels ({actual_ratio:.2f} ratio). "
            f"{spec['description']} requires a {target_w}:{target_h} ratio "
            f"(about {expected_ratio:.2f}). "
            f"Try an image that's about {spec['target_px'][0]}px wide "
            f"and {spec['target_px'][1]}px tall."
        )

    if errors:
        return False, errors, metadata

    return True, [], metadata
