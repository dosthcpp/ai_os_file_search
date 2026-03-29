"""
CLIP image/text embedding module for AI OS — Phase 3.

Provides 512-dimensional visual embeddings (CLIP ViT-B/32) for image files
and matching text query embeddings for cross-modal semantic search.

Architecture:
  - Image files  → get_image_embedding()  → 512-dim float vector
  - Text queries → get_text_embedding()   → 512-dim float vector
  Both vectors live in the same CLIP embedding space, so cosine similarity
  between a text vector and an image vector gives a meaningful relevance score.

The produced vectors are stored in the 'images_clip' ChromaDB collection
(separate from the 1536-dim 'files' collection) and searched via
GET /api/search/images in the Search API.

Dependencies (all optional — graceful fallback when absent):
    transformers>=4.30.0   — Hugging Face model hub + CLIPModel / CLIPProcessor
    torch>=2.0.0           — tensor backend required by the transformers CLIP model
    Pillow>=10.0.0         — image I/O

When any of these are missing, clip_available() returns False and all
embedding functions return None.  The file-indexer and search API degrade
gracefully: text-based search continues to work normally.

Model:
    openai/clip-vit-base-patch32  — ViT-B/32, 512-dim output
    Downloaded from Hugging Face Hub on first use (~350 MB, cached locally).
"""
from __future__ import annotations

from typing import Optional

# ── lazy module-level singletons (loaded once on first use) ───────────────────
_clip_checked: Optional[bool] = None  # None = not yet probed
_model = None
_processor = None

# Extensions eligible for CLIP visual indexing
CLIP_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
CLIP_DIM = 512  # output dimension of CLIP ViT-B/32


# ── availability probe ────────────────────────────────────────────────────────

def clip_available() -> bool:
    """
    Return True if transformers, torch, and Pillow are all importable.

    The check is performed once and cached; subsequent calls are O(1).
    """
    global _clip_checked
    if _clip_checked is not None:
        return _clip_checked
    try:
        import torch  # noqa: F401
        from transformers import CLIPModel, CLIPProcessor  # noqa: F401
        from PIL import Image  # noqa: F401
        _clip_checked = True
    except ImportError:
        _clip_checked = False
    return _clip_checked


# ── model loader (singleton) ──────────────────────────────────────────────────

def _load_clip():
    """
    Load and cache the CLIP ViT-B/32 model and its processor.

    Downloads from Hugging Face Hub on first call (~350 MB); subsequent
    calls return the cached objects immediately.
    """
    global _model, _processor
    if _model is None:
        from transformers import CLIPModel, CLIPProcessor
        _name = "openai/clip-vit-base-patch32"
        _processor = CLIPProcessor.from_pretrained(_name)
        _model = CLIPModel.from_pretrained(_name)
        _model.eval()  # inference mode — disables dropout, etc.
    return _model, _processor


# ── public embedding API ──────────────────────────────────────────────────────

def get_image_embedding(path: str) -> list[float] | None:
    """
    Generate a 512-dim CLIP visual embedding for the image at *path*.

    Steps:
      1. Open the image with Pillow and convert to RGB.
      2. Pre-process using CLIPProcessor (resize → centre-crop → normalise).
      3. Run the CLIP image encoder.
      4. L2-normalise the output so that cosine similarity equals dot product.

    Returns:
        A list of 512 floats, or None when CLIP is unavailable or the image
        cannot be processed (corrupt file, unsupported encoding, etc.).
    """
    if not clip_available():
        return None
    try:
        import torch
        from PIL import Image

        model, processor = _load_clip()
        img = Image.open(path).convert("RGB")
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            # L2-normalise: cosine_sim(a, b) == dot(a/‖a‖, b/‖b‖)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].tolist()
    except Exception:
        return None


def get_text_embedding(text: str) -> list[float] | None:
    """
    Generate a 512-dim CLIP text embedding for *text*.

    Used by the Search API to encode a natural-language query so it can be
    ranked against stored CLIP image embeddings via cosine similarity.

    CLIP text inputs are truncated at 77 tokens (model maximum).

    Returns:
        A list of 512 floats, or None when CLIP is unavailable.
    """
    if not clip_available():
        return None
    try:
        import torch

        model, processor = _load_clip()
        inputs = processor(
            text=[text],
            return_tensors="pt",
            truncation=True,
            max_length=77,  # CLIP text encoder maximum context length
        )
        with torch.no_grad():
            features = model.get_text_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].tolist()
    except Exception:
        return None
