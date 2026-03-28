def chunk_text(text: str, max_words: int = 400, overlap: int = 50) -> list[str]:
    """
    Split *text* into word-bounded chunks of at most *max_words* words.

    *overlap* controls how many words from the end of one chunk are repeated
    at the start of the next, preserving cross-boundary context for embedding.
    Overlap is clamped so it is always less than *max_words*.
    """
    if overlap >= max_words:
        overlap = max_words // 4

    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        # Next chunk starts *overlap* words before the end of this chunk
        start = end - overlap

    return chunks
