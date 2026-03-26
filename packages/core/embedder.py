"""
OpenAI embedding backend for AI OS.

Uses text-embedding-3-small (1536 dimensions) via the official openai SDK.
The OpenAI client is created lazily on first use and reused across calls.

Required environment variable:
    OPENAI_API_KEY  — your OpenAI API key
"""
from __future__ import annotations

import os

# Model and output dimension constants — import these wherever the dimension
# value is needed (e.g. when inserting zero-vectors as placeholders).
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

_client = None


def _get_client():
    """Return a singleton OpenAI client, creating it on first call."""
    global _client
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


def get_embedding(text: str) -> list[float]:
    """Return the embedding vector for *text* as a plain Python list of floats."""
    response = _get_client().embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding
