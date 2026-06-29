from typing import Any, Dict, List

from app.ingestion.chunker import chunk_text


def process_document(
    text: str,
    source: str,
    source_type: str,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> List[Dict[str, Any]]:
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    total = len(chunks)
    return [
        {
            "text": chunk,
            "source": source,
            "source_type": source_type,
            "chunk_index": i,
            "total_chunks": total,
        }
        for i, chunk in enumerate(chunks)
    ]
