"""
Tests for packages/file-indexer/ocr_extractor.py  (Phase 3 — OCR).

All tests mock Pillow and pytesseract so no OCR binary or image files are
required to run the test suite.
"""
from __future__ import annotations

import sys
import types
import unittest.mock as mock
from pathlib import Path

import pytest

# conftest.py adds file-indexer to sys.path so the import below resolves.
import ocr_extractor


# ── is_image() ────────────────────────────────────────────────────────────────

class TestIsImage:
    def test_png_recognised(self):
        assert ocr_extractor.is_image("/foo/bar.png") is True

    def test_jpg_recognised(self):
        assert ocr_extractor.is_image("/foo/photo.JPG") is True  # case-insensitive

    def test_jpeg_recognised(self):
        assert ocr_extractor.is_image("/some/file.jpeg") is True

    def test_bmp_recognised(self):
        assert ocr_extractor.is_image("/img.bmp") is True

    def test_tiff_recognised(self):
        assert ocr_extractor.is_image("/scan.tiff") is True

    def test_tif_recognised(self):
        assert ocr_extractor.is_image("/scan.tif") is True

    def test_gif_recognised(self):
        assert ocr_extractor.is_image("/anim.gif") is True

    def test_webp_recognised(self):
        assert ocr_extractor.is_image("/modern.webp") is True

    def test_py_not_recognised(self):
        assert ocr_extractor.is_image("/code.py") is False

    def test_pdf_not_recognised(self):
        assert ocr_extractor.is_image("/doc.pdf") is False

    def test_no_extension(self):
        assert ocr_extractor.is_image("/some/file") is False


# ── ocr_available() ───────────────────────────────────────────────────────────

class TestOcrAvailable:
    def test_returns_bool(self):
        assert isinstance(ocr_extractor.ocr_available(), bool)


# ── extract_text_from_image() ─────────────────────────────────────────────────

class TestExtractTextFromImage:
    def test_returns_none_when_ocr_unavailable(self, monkeypatch):
        """When OCR libs are missing, function must return None (no crash)."""
        monkeypatch.setattr(ocr_extractor, "_OCR_AVAILABLE", False)
        assert ocr_extractor.extract_text_from_image("/any/image.png") is None

    def test_returns_extracted_text(self, tmp_path, monkeypatch):
        """When pytesseract returns text, it should be returned stripped."""
        fake_img = mock.MagicMock()
        fake_img.__enter__ = mock.MagicMock(return_value=fake_img)
        fake_img.__exit__ = mock.MagicMock(return_value=False)
        fake_img.convert.return_value = fake_img

        # create=True allows patching even when PIL/pytesseract are not installed
        with mock.patch("ocr_extractor._OCR_AVAILABLE", True), \
             mock.patch("ocr_extractor.Image", create=True) as mock_image, \
             mock.patch("ocr_extractor.pytesseract", create=True) as mock_tess:
            mock_image.open.return_value = fake_img
            mock_tess.image_to_string.return_value = "  Hello, World!  "

            result = ocr_extractor.extract_text_from_image("/fake/image.png")

        assert result == "Hello, World!"

    def test_returns_none_when_empty_text(self, monkeypatch):
        """Empty OCR output should return None, not an empty string."""
        fake_img = mock.MagicMock()
        fake_img.__enter__ = mock.MagicMock(return_value=fake_img)
        fake_img.__exit__ = mock.MagicMock(return_value=False)
        fake_img.convert.return_value = fake_img

        with mock.patch("ocr_extractor._OCR_AVAILABLE", True), \
             mock.patch("ocr_extractor.Image", create=True) as mock_image, \
             mock.patch("ocr_extractor.pytesseract", create=True) as mock_tess:
            mock_image.open.return_value = fake_img
            mock_tess.image_to_string.return_value = "   \n  "

            result = ocr_extractor.extract_text_from_image("/fake/blank.png")

        assert result is None

    def test_returns_none_on_exception(self, monkeypatch):
        """Any exception during OCR must be swallowed and return None."""
        with mock.patch("ocr_extractor._OCR_AVAILABLE", True), \
             mock.patch("ocr_extractor.Image", create=True) as mock_image:
            mock_image.open.side_effect = OSError("file not found")

            result = ocr_extractor.extract_text_from_image("/nonexistent.png")

        assert result is None

    def test_image_converted_to_rgb(self, monkeypatch):
        """Image.convert('RGB') must be called before passing to pytesseract."""
        fake_img = mock.MagicMock()
        fake_img.__enter__ = mock.MagicMock(return_value=fake_img)
        fake_img.__exit__ = mock.MagicMock(return_value=False)
        fake_rgb = mock.MagicMock()
        fake_img.convert.return_value = fake_rgb

        with mock.patch("ocr_extractor._OCR_AVAILABLE", True), \
             mock.patch("ocr_extractor.Image", create=True) as mock_image, \
             mock.patch("ocr_extractor.pytesseract", create=True) as mock_tess:
            mock_image.open.return_value = fake_img
            mock_tess.image_to_string.return_value = "text"

            ocr_extractor.extract_text_from_image("/rgba.png")

        fake_img.convert.assert_called_once_with("RGB")
        mock_tess.image_to_string.assert_called_once_with(fake_rgb)
