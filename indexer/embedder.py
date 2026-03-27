"""
Embedder module — wraps OpenAI text-embedding-3-small.

Reads OPENAI_API_KEY from the environment. Raises a clear error if not set.
Vector dimension: 1536 (text-embedding-3-small default).
"""
import os

import openai

# Model name constant — change here to switch models project-wide
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# Lazy client — created on first call so import is always safe
_client: openai.OpenAI | None = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY environment variable is not set. "
                "Export it before starting the indexer."
            )
        _client = openai.OpenAI(api_key=api_key)
    return _client


def get_embedding(text: str) -> list[float]:
    """Return the embedding vector for *text* using OpenAI's embedding API."""
    # Truncate to ~8000 chars to stay well within the 8192-token limit
    text = text[:8000].replace("\n", " ")
    response = _get_client().embeddings.create(input=[text], model=EMBED_MODEL)
    return response.data[0].embedding
