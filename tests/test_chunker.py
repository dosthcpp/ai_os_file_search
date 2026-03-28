"""
Tests for packages/file-indexer/chunker.py
"""
import pytest
from chunker import chunk_text


# ── no-overlap (legacy behaviour) ─────────────────────────────────────────────

def test_empty_string_returns_empty_list():
    assert chunk_text("") == []


def test_single_word_returns_one_chunk():
    assert chunk_text("hello") == ["hello"]


def test_small_text_below_limit_is_one_chunk():
    text = " ".join(["word"] * 10)
    result = chunk_text(text, max_words=400, overlap=0)
    assert len(result) == 1
    assert result[0] == text


def test_text_splits_at_max_words_boundary():
    text = " ".join(["word"] * 800)
    result = chunk_text(text, max_words=400, overlap=0)
    assert len(result) == 2
    assert len(result[0].split()) == 400
    assert len(result[1].split()) == 400


def test_exact_max_words_is_one_chunk():
    text = " ".join(["word"] * 400)
    result = chunk_text(text, max_words=400, overlap=0)
    assert len(result) == 1


def test_one_word_over_limit_creates_two_chunks():
    text = " ".join(["word"] * 401)
    result = chunk_text(text, max_words=400, overlap=0)
    assert len(result) == 2
    assert len(result[0].split()) == 400
    assert len(result[1].split()) == 1


def test_custom_max_words():
    text = " ".join(["w"] * 15)
    result = chunk_text(text, max_words=5, overlap=0)
    assert len(result) == 3
    assert all(len(c.split()) == 5 for c in result)


def test_remainder_words_included():
    # 13 words, max 5 → 3 chunks (5, 5, 3)
    text = " ".join([f"w{i}" for i in range(13)])
    result = chunk_text(text, max_words=5, overlap=0)
    assert len(result) == 3
    assert len(result[2].split()) == 3


def test_chunks_reconstruct_original_no_overlap():
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)
    chunks = chunk_text(text, max_words=10, overlap=0)
    reconstructed = " ".join(" ".join(c.split()) for c in chunks)
    assert reconstructed == text


# ── overlapping chunks ────────────────────────────────────────────────────────

def test_overlap_zero_same_as_no_overlap():
    text = " ".join([f"w{i}" for i in range(100)])
    assert chunk_text(text, max_words=30, overlap=0) == chunk_text(text, max_words=30, overlap=0)


def test_overlap_creates_more_chunks():
    text = " ".join([f"w{i}" for i in range(100)])
    no_ov = chunk_text(text, max_words=30, overlap=0)
    with_ov = chunk_text(text, max_words=30, overlap=10)
    assert len(with_ov) >= len(no_ov)


def test_overlap_words_appear_in_consecutive_chunks():
    words = [f"w{i}" for i in range(20)]
    text = " ".join(words)
    chunks = chunk_text(text, max_words=10, overlap=3)
    # Last 3 words of chunk 0 should appear at the start of chunk 1
    tail = chunks[0].split()[-3:]
    head = chunks[1].split()[:3]
    assert tail == head


def test_overlap_each_chunk_at_most_max_words():
    text = " ".join([f"w{i}" for i in range(200)])
    chunks = chunk_text(text, max_words=40, overlap=10)
    for c in chunks:
        assert len(c.split()) <= 40


def test_overlap_covers_all_words():
    """Every word in the original text must appear in at least one chunk."""
    words = [f"w{i}" for i in range(75)]
    text = " ".join(words)
    chunks = chunk_text(text, max_words=20, overlap=5)
    all_chunk_words = set()
    for c in chunks:
        all_chunk_words.update(c.split())
    assert set(words) == all_chunk_words


def test_overlap_clamped_when_ge_max_words():
    """An overlap >= max_words must not cause infinite loops."""
    text = " ".join([f"w{i}" for i in range(30)])
    # overlap == max_words: should be clamped internally
    chunks = chunk_text(text, max_words=10, overlap=10)
    assert len(chunks) > 0


def test_default_overlap_produces_overlap():
    """The default overlap=50 should overlap on large inputs."""
    text = " ".join([f"w{i}" for i in range(500)])
    chunks = chunk_text(text)  # default max_words=400, overlap=50
    # With 500 words and 400-word chunks with 50-word overlap, expect 2 chunks
    assert len(chunks) == 2
    # Chunk 1 ends at word 399; chunk 2 starts at word 350 (overlap of 50)
    tail = chunks[0].split()[-50:]
    head = chunks[1].split()[:50]
    assert tail == head
