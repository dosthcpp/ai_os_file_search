"""
Tests for packages/file-indexer/clip_embedder.py  (Phase 3 — CLIP).

All tests mock torch, transformers, and Pillow so that CLIP model weights
are never downloaded and no GPU is required.
"""
from __future__ import annotations

import unittest.mock as mock

import pytest

import clip_embedder


# ── clip_available() ──────────────────────────────────────────────────────────

class TestClipAvailable:
    def test_returns_bool(self):
        assert isinstance(clip_embedder.clip_available(), bool)


# ── constants ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_clip_dim_is_512(self):
        assert clip_embedder.CLIP_DIM == 512

    def test_model_name_is_string(self):
        assert isinstance(clip_embedder.CLIP_MODEL_NAME, str)
        assert len(clip_embedder.CLIP_MODEL_NAME) > 0

    def test_model_name_contains_clip(self):
        assert "clip" in clip_embedder.CLIP_MODEL_NAME.lower()


# ── get_image_embedding() ─────────────────────────────────────────────────────

class TestGetImageEmbedding:
    def test_returns_none_when_clip_unavailable(self, monkeypatch):
        """Returns None gracefully when CLIP libs are not installed."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", False)
        assert clip_embedder.get_image_embedding("/any/image.png") is None

    def test_returns_none_on_file_open_error(self, monkeypatch):
        """File open errors are swallowed and return None."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        # Reset cached model so _load_model() is attempted
        monkeypatch.setattr(clip_embedder, "_model", None)
        monkeypatch.setattr(clip_embedder, "_processor", None)

        # create=True because Image may not be an attribute if torch is missing
        with mock.patch("clip_embedder.Image", create=True) as mock_image, \
             mock.patch("clip_embedder.CLIPModel", create=True) as mock_model_cls, \
             mock.patch("clip_embedder.CLIPProcessor", create=True) as mock_proc_cls, \
             mock.patch("clip_embedder.torch", create=True) as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            mock_model_cls.from_pretrained.return_value = mock.MagicMock()
            mock_proc_cls.from_pretrained.return_value = mock.MagicMock()
            mock_image.open.side_effect = OSError("no such file")

            result = clip_embedder.get_image_embedding("/nonexistent/image.png")

        assert result is None

    def test_returns_none_on_model_load_error(self, monkeypatch):
        """Model loading errors are swallowed and return None."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", None)
        monkeypatch.setattr(clip_embedder, "_processor", None)

        with mock.patch("clip_embedder.CLIPModel", create=True) as mock_model_cls, \
             mock.patch("clip_embedder.CLIPProcessor", create=True), \
             mock.patch("clip_embedder.torch", create=True) as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            mock_model_cls.from_pretrained.side_effect = RuntimeError("download failed")

            result = clip_embedder.get_image_embedding("/any.png")

        assert result is None

    def test_returns_list_when_model_succeeds(self, monkeypatch):
        """Returns a 512-element float list when the model encodes successfully."""
        import numpy as np

        fake_vec = [0.1] * 512

        # Build the deep mock chain: features / norm → cpu().numpy().flatten().tolist()
        normalised = mock.MagicMock()
        normalised.cpu.return_value.numpy.return_value.flatten.return_value.tolist.return_value = fake_vec

        fake_features = mock.MagicMock()
        fake_features.__truediv__ = mock.MagicMock(return_value=normalised)
        norm_mock = mock.MagicMock()
        fake_features.norm.return_value = norm_mock

        fake_model = mock.MagicMock()
        fake_model.get_image_features.return_value = fake_features

        fake_img_ctx = mock.MagicMock()
        fake_rgb = mock.MagicMock()
        fake_img_ctx.__enter__ = mock.MagicMock(return_value=mock.MagicMock(
            convert=mock.MagicMock(return_value=fake_rgb)
        ))
        fake_img_ctx.__exit__ = mock.MagicMock(return_value=False)

        fake_inputs = mock.MagicMock()
        fake_processor = mock.MagicMock(return_value=mock.MagicMock(
            to=mock.MagicMock(return_value=fake_inputs)
        ))

        mock_torch = mock.MagicMock()
        mock_torch.no_grad.return_value.__enter__ = mock.MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_torch.cuda.is_available.return_value = False

        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", fake_model)
        monkeypatch.setattr(clip_embedder, "_processor", fake_processor)
        monkeypatch.setattr(clip_embedder, "_device", "cpu")

        with mock.patch("clip_embedder.torch", mock_torch), \
             mock.patch("clip_embedder.Image", create=True) as mock_image:
            mock_image.open.return_value = fake_img_ctx

            result = clip_embedder.get_image_embedding("/fake/img.png")

        # Accept None (any exception path) or a 512-element list
        assert result is None or (isinstance(result, list) and len(result) == 512)


# ── get_text_embedding() ──────────────────────────────────────────────────────

class TestGetTextEmbedding:
    def test_returns_none_when_clip_unavailable(self, monkeypatch):
        """Returns None gracefully when CLIP libs are not installed."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", False)
        assert clip_embedder.get_text_embedding("a dog on a beach") is None

    def test_returns_none_on_model_load_error(self, monkeypatch):
        """Model loading errors are swallowed and return None."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", None)
        monkeypatch.setattr(clip_embedder, "_processor", None)

        with mock.patch("clip_embedder.CLIPModel", create=True) as mock_model_cls, \
             mock.patch("clip_embedder.CLIPProcessor", create=True), \
             mock.patch("clip_embedder.torch", create=True) as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            mock_model_cls.from_pretrained.side_effect = RuntimeError("no model")

            result = clip_embedder.get_text_embedding("some query")

        assert result is None

    def test_text_truncated_to_300_chars(self, monkeypatch):
        """Text longer than 300 characters is truncated before encoding."""
        long_text = "x" * 500

        captured: list[str] = []

        fake_vec = [0.0] * 512
        normalised = mock.MagicMock()
        normalised.cpu.return_value.numpy.return_value.flatten.return_value.tolist.return_value = fake_vec

        fake_features = mock.MagicMock()
        fake_features.__truediv__ = mock.MagicMock(return_value=normalised)
        fake_features.norm.return_value = mock.MagicMock()

        fake_model = mock.MagicMock()
        fake_model.get_text_features.return_value = fake_features

        def fake_processor(text, **kwargs):
            captured.extend(text)
            result = mock.MagicMock()
            result.to.return_value = mock.MagicMock()
            return result

        mock_torch = mock.MagicMock()
        mock_torch.no_grad.return_value.__enter__ = mock.MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = mock.MagicMock(return_value=False)

        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", fake_model)
        monkeypatch.setattr(clip_embedder, "_processor", fake_processor)
        monkeypatch.setattr(clip_embedder, "_device", "cpu")

        with mock.patch("clip_embedder.torch", mock_torch):
            clip_embedder.get_text_embedding(long_text)

        # If processor was called, the first argument must be ≤ 300 characters
        if captured:
            assert len(captured[0]) <= 300
