def chunk_text(text: str, max_words=400):
    words = text.split()
    chunks, buf = [], []

    for w in words:
        buf.append(w)
        if len(buf) >= max_words:
            chunks.append(" ".join(buf))
            buf = []

    if buf:
        chunks.append(" ".join(buf))

    return chunks
