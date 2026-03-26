"""
Tests for packages/file-indexer/chunker.py
"""
import pytest
from chunker import chunk_text


def test_empty_string_returns_empty_list():
    assert chunk_text("") == []


def test_single_word_returns_one_chunk():
    result = chunk_text("hello")
    assert result == ["hello"]


def test_small_text_below_limit_is_one_chunk():
    text = " ".join(["word"] * 10)
    result = chunk_text(text, max_words=400)
    assert len(result) == 1
    assert result[0] == text


def test_text_splits_at_max_words_boundary():
    text = " ".join(["word"] * 800)
    result = chunk_text(text, max_words=400)
    assert len(result) == 2
    assert len(result[0].split()) == 400
    assert len(result[1].split()) == 400


def test_exact_max_words_is_one_chunk():
    text = " ".join(["word"] * 400)
    result = chunk_text(text, max_words=400)
    assert len(result) == 1


def test_one_word_over_limit_creates_two_chunks():
    text = " ".join(["word"] * 401)
    result = chunk_text(text, max_words=400)
    assert len(result) == 2
    assert len(result[0].split()) == 400
    assert len(result[1].split()) == 1


def test_custom_max_words():
    text = " ".join(["w"] * 15)
    result = chunk_text(text, max_words=5)
    assert len(result) == 3
    assert all(len(c.split()) == 5 for c in result)


def test_remainder_words_included():
    # 13 words, max 5 → 3 chunks (5, 5, 3)
    text = " ".join([f"w{i}" for i in range(13)])
    result = chunk_text(text, max_words=5)
    assert len(result) == 3
    assert len(result[2].split()) == 3


def test_chunks_reconstruct_original():
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)
    chunks = chunk_text(text, max_words=10)
    reconstructed = " ".join(" ".join(c.split()) for c in chunks)
    assert reconstructed == text
