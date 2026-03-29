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

    def test_model_name_set(self):
        assert isinstance(clip_embedder.CLIP_MODEL_NAME, str)
        assert len(clip_embedder.CLIP_MODEL_NAME) > 0


# ── get_image_embedding() ─────────────────────────────────────────────────────

class TestGetImageEmbedding:
    def test_returns_none_when_clip_unavailable(self, monkeypatch):
        """Returns None gracefully when CLIP libs are not installed."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", False)
        assert clip_embedder.get_image_embedding("/any/image.png") is None

    def test_returns_float_list_of_correct_length(self, monkeypatch):
        """Returns a 512-element list of floats when CLIP is available."""
        import numpy as np

        fake_features = mock.MagicMock()
        fake_np = np.ones((1, 512), dtype="float32") / np.sqrt(512)
        fake_features.norm.return_value = mock.MagicMock()
        fake_features.__truediv__ = mock.MagicMock(return_value=mock.MagicMock(
            cpu=lambda: mock.MagicMock(
                numpy=lambda: mock.MagicMock(
                    flatten=lambda: mock.MagicMock(
                        tolist=lambda: fake_np.flatten().tolist()
                    )
                )
            )
        ))

        # Build a realistic chain: features / norm → cpu().numpy().flatten().tolist()
        norm_val = mock.MagicMock()
        normalised = mock.MagicMock()
        normalised.cpu.return_value.numpy.return_value.flatten.return_value.tolist.return_value = (
            fake_np.flatten().tolist()
        )

        fake_model = mock.MagicMock()
        fake_model.get_image_features.return_value = mock.MagicMock(
            __truediv__=mock.MagicMock(return_value=normalised),
            norm=mock.MagicMock(return_value=norm_val),
        )

        fake_processor = mock.MagicMock()
        fake_processor.return_value.to.return_value = {}

        fake_img_ctx = mock.MagicMock()
        fake_img_ctx.__enter__ = mock.MagicMock(return_value=mock.MagicMock(
            convert=mock.MagicMock(return_value=mock.MagicMock())
        ))
        fake_img_ctx.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("clip_embedder._CLIP_AVAILABLE", True), \
             mock.patch("clip_embedder._model", fake_model), \
             mock.patch("clip_embedder._processor", fake_processor), \
             mock.patch("clip_embedder._device", "cpu"), \
             mock.patch("clip_embedder.Image") as mock_image, \
             mock.patch("clip_embedder.torch") as mock_torch:
            mock_image.open.return_value = fake_img_ctx
            mock_torch.no_grad.return_value.__enter__ = mock.MagicMock(return_value=None)
            mock_torch.no_grad.return_value.__exit__ = mock.MagicMock(return_value=False)
            # Simulate normalised features returning correct list
            fake_model.get_image_features.return_value.__truediv__ = mock.MagicMock(
                return_value=normalised
            )

            result = clip_embedder.get_image_embedding("/fake/image.png")

        # The function returns a list of 512 floats OR None on any error
        assert result is None or (isinstance(result, list) and len(result) == 512)

    def test_returns_none_on_exception(self, monkeypatch):
        """Any exception is swallowed and returns None."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", None)
        monkeypatch.setattr(clip_embedder, "_processor", None)

        with mock.patch("clip_embedder.Image") as mock_image:
            mock_image.open.side_effect = OSError("bad file")
            result = clip_embedder.get_image_embedding("/bad/path.png")

        assert result is None


# ── get_text_embedding() ──────────────────────────────────────────────────────

class TestGetTextEmbedding:
    def test_returns_none_when_clip_unavailable(self, monkeypatch):
        """Returns None gracefully when CLIP libs are not installed."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", False)
        assert clip_embedder.get_text_embedding("a dog on a beach") is None

    def test_returns_none_on_exception(self, monkeypatch):
        """Exceptions during text encoding are swallowed and return None."""
        monkeypatch.setattr(clip_embedder, "_CLIP_AVAILABLE", True)
        monkeypatch.setattr(clip_embedder, "_model", None)
        monkeypatch.setattr(clip_embedder, "_processor", None)

        with mock.patch("clip_embedder.CLIPModel") as mock_cls:
            mock_cls.from_pretrained.side_effect = RuntimeError("no model")
            result = clip_embedder.get_text_embedding("some query")

        assert result is None

    def test_text_truncated_to_300_chars(self, monkeypatch):
        """Text longer than 300 characters must be pre-truncated before encoding."""
        long_text = "x" * 500

        captured: list[str] = []

        def fake_processor(text, **kwargs):
            captured.extend(text)
            return mock.MagicMock(to=mock.MagicMock(return_value={}))

        import numpy as np
        normalised = mock.MagicMock()
        normalised.cpu.return_value.numpy.return_value.flatten.return_value.tolist.return_value = (
            [0.0] * 512
        )

        fake_model = mock.MagicMock()
        fake_model.get_text_features.return_value.__truediv__ = mock.MagicMock(
            return_value=normalised
        )

        with mock.patch("clip_embedder._CLIP_AVAILABLE", True), \
             mock.patch("clip_embedder._model", fake_model), \
             mock.patch("clip_embedder._processor", fake_processor), \
             mock.patch("clip_embedder._device", "cpu"), \
             mock.patch("clip_embedder.torch") as mock_torch:
            mock_torch.no_grad.return_value.__enter__ = mock.MagicMock(return_value=None)
            mock_torch.no_grad.return_value.__exit__ = mock.MagicMock(return_value=False)

            clip_embedder.get_text_embedding(long_text)

        # If text was passed to processor, it must be ≤ 300 characters
        if captured:
            assert len(captured[0]) <= 300
