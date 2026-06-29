from typing import List


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks, breaking at sentence or word boundaries."""
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Prefer sentence boundary, fall back to word boundary
        boundary = text.rfind(". ", start, end)
        if boundary == -1 or boundary < start + chunk_size // 2:
            boundary = text.rfind(" ", start, end)
        if boundary <= start:
            boundary = end

        chunks.append(text[start:boundary].strip())
        start = max(start + 1, boundary - overlap)

    return [c for c in chunks if c]
