"""
AI OS Phase 3 — Image Indexer

Coordinates two independent indexing pipelines for each image file:

  1. OCR pipeline  (text-in-image → text search)
     pytesseract extracts visible text → chunk → OpenAI text-embedding-3-small
     → uploaded to the existing 'files' ChromaDB collection.
     OCR results therefore appear in standard /api/search results alongside
     regular text documents.

  2. CLIP pipeline  (visual semantics → image search)
     CLIP ViT-B/32 encodes the image as a 512-dim vector → uploaded to the
     separate 'images_clip' ChromaDB collection.
     At query time the CLIP *text* encoder embeds the user's query into the
     same 512-dim space, enabling cross-modal retrieval via /api/search/images.

Either pipeline degrades gracefully when its optional dependencies
(pytesseract / transformers+torch) are not installed.

Public API
----------
index_image(path, file_hash)   — run both pipelines for one image file
delete_image(path)             — remove image data from both collections
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── resolve sibling packages ──────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "packages" / "core"))

# Text embedding (OpenAI text-embedding-3-small, 1536-dim)
from embedder import get_embedding  # noqa: E402

# CLIP image/text embedding (ViT-B/32, 512-dim)
from clip_embedder import (  # noqa: E402
    clip_available,
    get_image_embedding,
)

# OCR text extraction
from ocr_extractor import extract_text_from_image, ocr_available  # noqa: E402

# Chunking (reuse the same word-based chunker as text documents)
from chunker import chunk_text  # noqa: E402

# HTTP client to the Search API server
from client import (  # noqa: E402
    delete_chunks,
    delete_image_embedding,
    send_file_change,
    upload_chunk,
    upload_image_embedding,
)

# State management (shared with the text indexer)
from utils import chunk_id_to_uuid, load_state, save_state, update_state  # noqa: E402


# ── public API ────────────────────────────────────────────────────────────────

def index_image(path: str, file_hash: str) -> None:
    """
    Index one image file through both the OCR and CLIP pipelines.

    Parameters
    ----------
    path      : absolute path to the image file
    file_hash : MD5 hex digest of the file (used to generate stable chunk IDs)
    """
    ext = os.path.splitext(path)[1].lower()

    # ── Pipeline 1: OCR → text embedding → 'files' collection ────────────────
    ocr_chunk_ids = _index_ocr(path, file_hash, ext)

    # ── Pipeline 2: CLIP image embedding → 'images_clip' collection ──────────
    _index_clip(path, file_hash)

    # Record state so the indexer can detect future modifications / deletions
    if ocr_chunk_ids is not None:
        # Reuse the existing state schema; CLIP vector is stored separately
        state = load_state()
        prev = state.get(path, {})
        update_state(
            path=path,
            file_hash=file_hash,
            chunk_ids=ocr_chunk_ids,
            stat=os.stat(path),
            text="",          # raw text not stored for images in state
            version=prev.get("version", 0) + 1,
        )

    send_file_change(path, "added")
    print(f"[IMG] Indexed {path}", flush=True)


def delete_image(path: str) -> None:
    """
    Remove all indexed data for an image file:
      - OCR text chunks from the 'files' collection
      - CLIP embedding from the 'images_clip' collection
    """
    state = load_state()
    info = state.get(path)

    if info:
        chunk_ids = info.get("chunks", [])
        if chunk_ids:
            delete_chunks(chunk_ids)
        state.pop(path, None)
        save_state(state)

    # Remove CLIP embedding regardless of whether OCR state existed
    delete_image_embedding(path)
    send_file_change(path, "deleted")
    print(f"[IMG] Deleted {path}", flush=True)


# ── internal helpers ──────────────────────────────────────────────────────────

def _index_ocr(path: str, file_hash: str, ext: str) -> list[str] | None:
    """
    Run OCR on *path*, chunk the result, embed each chunk with OpenAI, and
    upload to the 'files' ChromaDB collection.

    Returns the list of chunk IDs on success, or None when OCR produces no text.
    """
    if not ocr_available():
        print(f"[IMG] OCR unavailable, skipping text extraction for {path}", flush=True)
        return None

    text = extract_text_from_image(path)
    if not text:
        print(f"[IMG] No OCR text detected in {path}", flush=True)
        return None

    chunks = chunk_text(text)
    chunk_ids: list[str] = []

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        cid = chunk_id_to_uuid(f"{file_hash}_ocr_{i}")
        chunk_ids.append(cid)
        upload_chunk(
            chunk_id=cid,
            vector=emb,
            payload={
                "path": path,
                "chunk_index": i,
                "text": chunk[:300],
                "ext": ext,
                "source": "ocr",         # tag so UI can distinguish OCR hits
            },
        )

    print(f"[IMG] OCR uploaded {len(chunk_ids)} chunk(s) for {path}", flush=True)
    return chunk_ids


def _index_clip(path: str, file_hash: str) -> None:
    """
    Compute a CLIP visual embedding for *path* and send it to the search API
    which stores it in the 'images_clip' ChromaDB collection.
    """
    if not clip_available():
        print(f"[IMG] CLIP unavailable, skipping visual embedding for {path}", flush=True)
        return

    vector = get_image_embedding(path)
    if vector is None:
        print(f"[IMG] CLIP embedding failed for {path}", flush=True)
        return

    upload_image_embedding(path=path, image_vector=vector, file_hash=file_hash)
    print(f"[IMG] CLIP embedding uploaded for {path}", flush=True)
