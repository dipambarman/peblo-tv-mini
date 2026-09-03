from app.utils.image_validation import validate_artwork
from io import BytesIO
from PIL import Image

def create_test_image(width: int, height: int, format: str = "JPEG") -> bytes:
    """Helper to create dummy image bytes for testing."""
    file = BytesIO()
    image = Image.new("RGB", size=(width, height), color=(153, 153, 255))
    image.save(file, format)
    return file.getvalue()

def test_validate_poster_success():
    """Test poster image validation succeeds with 2:3 ratio and under 200kb."""
    img_bytes = create_test_image(600, 900)
    is_valid, errors, metadata = validate_artwork(img_bytes, "image/jpeg", "poster")
    assert is_valid is True
    assert len(errors) == 0
    assert metadata["width"] == 600
    assert metadata["height"] == 900

def test_validate_banner_wrong_ratio():
    """Test banner image validation fails if aspect ratio is totally wrong (e.g. 1:1 instead of 16:9)."""
    img_bytes = create_test_image(1000, 1000)
    is_valid, errors, metadata = validate_artwork(img_bytes, "image/jpeg", "banner")
    assert is_valid is False
    assert len(errors) > 0
    assert "requires a 16:9 ratio" in errors[0]

def test_validate_thumbnail_too_large():
    """Test thumbnail image validation fails if file is too large (over 200kb)."""
    # Create a very large image to exceed 200kb
    img_bytes = create_test_image(4000, 2250)
    # Depending on compression it might still be small, so we can artificially bloat it
    bloated_bytes = img_bytes + (b"0" * 300_000)
    
    is_valid, errors, metadata = validate_artwork(bloated_bytes, "image/jpeg", "thumbnail")
    assert is_valid is False
    assert any("maximum allowed size is 200 KB" in err for err in errors)

def test_validate_invalid_content_type():
    """Test rejection of unsupported file types."""
    img_bytes = create_test_image(600, 900)
    is_valid, errors, metadata = validate_artwork(img_bytes, "application/pdf", "poster")
    assert is_valid is False
    assert len(errors) > 0
    assert "This file type isn't supported" in errors[0]

def test_validate_invalid_artwork_type():
    """Test rejection of unknown slots."""
    img_bytes = create_test_image(600, 900)
    is_valid, errors, metadata = validate_artwork(img_bytes, "image/jpeg", "unknown_slot")
    assert is_valid is False
    assert len(errors) > 0
    assert "Unknown artwork type" in errors[0]
