"""
AI OS — OCR Text Extractor  (Phase 3)

Extracts visible text from image files using Tesseract OCR via pytesseract.

Supported formats: PNG, JPEG, BMP, TIFF, GIF, WebP.

Optional dependency: pytesseract + Pillow.
Returns None gracefully when either library is missing or the Tesseract
binary is not installed.  All other errors (corrupt file, unreadable image)
are also caught and return None so callers never crash.
"""
from __future__ import annotations

import os

# Image extensions handled by this module
IMAGE_EXTS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
)

# Optional runtime dependencies — OCR requires both Pillow and pytesseract
try:
    from PIL import Image
    import pytesseract
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False


# ── public API ────────────────────────────────────────────────────────────────

def is_image(path: str) -> bool:
    """Return True if *path* carries an extension supported by this module."""
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def ocr_available() -> bool:
    """Return True when pytesseract and Pillow are importable."""
    return _OCR_AVAILABLE


def extract_text_from_image(path: str) -> str | None:
    """
    Extract visible text from the image at *path* using Tesseract OCR.

    The image is converted to RGB before OCR to handle RGBA and palette-mode
    images without crashing Tesseract.

    Returns:
        Stripped text string — or None when:
        - pytesseract / Pillow are not installed
        - Tesseract binary is unavailable
        - The image cannot be opened or processed
        - No text was detected (empty result)
    """
    if not _OCR_AVAILABLE:
        return None
    try:
        with Image.open(path) as img:
            # RGB conversion ensures compatibility (RGBA, palette, greyscale, etc.)
            text: str = pytesseract.image_to_string(img.convert("RGB")).strip()
        return text if text else None
    except Exception:
        return None
