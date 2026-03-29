"""
AI OS — CLIP Image Embedder  (Phase 3)

Generates 512-dimensional visual embeddings for image files using the OpenAI
CLIP model (ViT-B/32) loaded through the Hugging Face *transformers* library.

Two public functions are provided:

    get_image_embedding(path)  → 512-dim float list
        Visual embedding for an image file.

    get_text_embedding(text)   → 512-dim float list
        Text embedding in the *same* space as image embeddings.
        Use this to embed search queries for image retrieval.

Both vectors are L2-normalised (unit length), so cosine similarity is
equivalent to a simple dot product.

The model is loaded lazily on first use and cached for the lifetime of the
process.  GPU is used automatically when CUDA is available; otherwise CPU.

Optional dependency: transformers + torch + Pillow.
All functions return None gracefully when any dependency is missing.
"""
from __future__ import annotations

from typing import Optional

# CLIP model identifier on the Hugging Face Hub
CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"

# Embedding dimension for ViT-B/32 (must match the ChromaDB collection schema)
CLIP_DIM: int = 512

# Optional runtime imports — CLIP requires transformers, torch, and Pillow.
# Always define module-level names so mock.patch can replace them in tests.
try:
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    _CLIP_AVAILABLE = True
except ImportError:
    torch = None        # type: ignore[assignment]
    Image = None        # type: ignore[assignment]
    CLIPModel = None    # type: ignore[assignment]
    CLIPProcessor = None  # type: ignore[assignment]
    _CLIP_AVAILABLE = False

# Lazy singletons — loaded once on first use
_model: Optional["CLIPModel"] = None      # type: ignore[name-defined]
_processor: Optional["CLIPProcessor"] = None  # type: ignore[name-defined]
_device: str = "cpu"


# ── public API ────────────────────────────────────────────────────────────────

def clip_available() -> bool:
    """Return True when transformers, torch, and Pillow are all importable."""
    return _CLIP_AVAILABLE


def get_image_embedding(path: str) -> Optional[list[float]]:
    """
    Return a 512-dim L2-normalised CLIP visual embedding for the image at *path*.

    The image is converted to RGB before encoding to handle RGBA, palette,
    and greyscale formats without errors.

    Returns None when CLIP is unavailable or any processing error occurs.
    """
    if not _CLIP_AVAILABLE:
        return None
    try:
        model, processor, device = _load_model()
        with Image.open(path) as img:
            inputs = processor(
                images=img.convert("RGB"), return_tensors="pt"
            ).to(device)
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten().tolist()
    except Exception:
        return None


def get_text_embedding(text: str) -> Optional[list[float]]:
    """
    Return a 512-dim L2-normalised CLIP text embedding for *text*.

    The embedding lives in the same vector space as image embeddings so a
    cosine search against an `images_clip` ChromaDB collection returns
    semantically relevant images for a text query.

    Returns None when CLIP is unavailable or any processing error occurs.
    """
    if not _CLIP_AVAILABLE:
        return None
    try:
        model, processor, device = _load_model()
        # Pre-truncate to ~300 characters; CLIP tokeniser handles the rest
        inputs = processor(
            text=[text[:300]], return_tensors="pt", padding=True
        ).to(device)
        with torch.no_grad():
            features = model.get_text_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten().tolist()
    except Exception:
        return None


# ── internal helpers ──────────────────────────────────────────────────────────

def _load_model():
    """Load the CLIP model and processor on first call; return cached objects."""
    global _model, _processor, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(_device)
        _processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
        _model.eval()
        print(f"[CLIP] Model loaded on {_device}", flush=True)
    return _model, _processor, _device
