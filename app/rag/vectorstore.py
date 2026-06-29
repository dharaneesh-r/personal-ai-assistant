import uuid
from functools import lru_cache
from typing import Any, Dict, List

import chromadb

from app.config import settings
from app.rag.embeddings import embed_texts

COLLECTION_NAME = "documents"


@lru_cache(maxsize=1)
def _get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_db_path)


def _get_collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: List[Dict[str, Any]]) -> int:
    if not chunks:
        return 0

    collection = _get_collection()
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    collection.add(
        ids=[str(uuid.uuid4()) for _ in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "source": c["source"],
                "source_type": c["source_type"],
                "chunk_index": c["chunk_index"],
                "total_chunks": c["total_chunks"],
            }
            for c in chunks
        ],
    )
    return len(chunks)


def list_sources() -> List[Dict[str, Any]]:
    collection = _get_collection()
    result = collection.get(include=["metadatas"])

    seen: Dict[str, Dict] = {}
    for meta in result["metadatas"]:
        src = meta["source"]
        if src not in seen:
            seen[src] = {"source": src, "source_type": meta["source_type"], "chunk_count": 0}
        seen[src]["chunk_count"] += 1

    return list(seen.values())


def delete_source(source: str) -> int:
    collection = _get_collection()
    result = collection.get(where={"source": source})
    ids = result["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    results = collection.query(
        query_embeddings=[embed_texts([query])[0]],
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"],
    )

    return [
        {
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "source_type": results["metadatas"][0][i]["source_type"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "score": round(1 - results["distances"][0][i], 4),
        }
        for i in range(len(results["ids"][0]))
    ]
