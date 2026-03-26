"""
Tests for packages/core/embedder.py (OpenAI embedding backend).

All tests mock the OpenAI client to avoid real API calls.
"""
import importlib
import pytest
from unittest.mock import MagicMock, patch


def _reset_module():
    """Reset the module-level singleton so each test starts fresh."""
    import embedder
    embedder._client = None
    importlib.reload(embedder)
    return embedder


def _mock_openai_client(embedding: list[float]):
    """Return a mock OpenAI client whose embeddings.create returns `embedding`."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=embedding)]
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response
    return mock_client


# ── basic contract ────────────────────────────────────────────────────────────

def test_get_embedding_returns_list():
    """get_embedding must return a plain Python list."""
    import embedder as emb_module
    emb_module._client = None
    fake_vec = [0.1] * emb_module.EMBEDDING_DIM
    mock_client = _mock_openai_client(fake_vec)

    with patch("openai.OpenAI", return_value=mock_client):
        emb_module._client = None
        result = emb_module.get_embedding("hello world")

    assert isinstance(result, list)


def test_get_embedding_correct_dimension():
    """Returned vector length must equal EMBEDDING_DIM."""
    import embedder as emb_module
    emb_module._client = None
    dim = emb_module.EMBEDDING_DIM
    fake_vec = [float(i) / dim for i in range(dim)]
    mock_client = _mock_openai_client(fake_vec)

    with patch("openai.OpenAI", return_value=mock_client):
        emb_module._client = None
        result = emb_module.get_embedding("test input")

    assert len(result) == dim


def test_get_embedding_values_are_floats():
    """All elements in the returned list must be floats."""
    import embedder as emb_module
    emb_module._client = None
    fake_vec = [0.5] * emb_module.EMBEDDING_DIM
    mock_client = _mock_openai_client(fake_vec)

    with patch("openai.OpenAI", return_value=mock_client):
        emb_module._client = None
        result = emb_module.get_embedding("some text")

    assert all(isinstance(v, float) for v in result)


# ── API call behaviour ────────────────────────────────────────────────────────

def test_get_embedding_calls_correct_model():
    """embeddings.create must be called with the configured model name."""
    import embedder as emb_module
    emb_module._client = None
    fake_vec = [0.0] * emb_module.EMBEDDING_DIM
    mock_client = _mock_openai_client(fake_vec)

    with patch("openai.OpenAI", return_value=mock_client):
        emb_module._client = None
        emb_module.get_embedding("model check")

    mock_client.embeddings.create.assert_called_once_with(
        input="model check",
        model=emb_module.EMBEDDING_MODEL,
    )


def test_get_embedding_client_reused_across_calls():
    """OpenAI() constructor must be called only once (lazy singleton)."""
    import embedder as emb_module
    emb_module._client = None
    fake_vec = [0.0] * emb_module.EMBEDDING_DIM
    mock_client = _mock_openai_client(fake_vec)

    with patch("openai.OpenAI", return_value=mock_client) as mock_constructor:
        emb_module._client = None
        emb_module.get_embedding("first call")
        emb_module.get_embedding("second call")
        assert mock_constructor.call_count == 1


# ── constants ─────────────────────────────────────────────────────────────────

def test_embedding_dim_is_1536():
    """EMBEDDING_DIM must equal 1536 (text-embedding-3-small)."""
    import embedder as emb_module
    assert emb_module.EMBEDDING_DIM == 1536


def test_embedding_model_constant_defined():
    """EMBEDDING_MODEL must be a non-empty string."""
    import embedder as emb_module
    assert isinstance(emb_module.EMBEDDING_MODEL, str)
    assert len(emb_module.EMBEDDING_MODEL) > 0
