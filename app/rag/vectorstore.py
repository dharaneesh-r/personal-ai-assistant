import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings
from app.rag.embeddings import embed_texts

COLLECTION_NAME = "documents"
VECTOR_SIZE = 384  # default for all-MiniLM-L6-v2


@lru_cache(maxsize=1)
def _get_client() -> QdrantClient:
    if settings.qdrant_url and settings.qdrant_api_key:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    else:
        client = QdrantClient(path=settings.qdrant_path)

    # Ensure collection exists
    try:
        client.get_collection(COLLECTION_NAME)
    except UnexpectedResponse as e:
        if "Not found" in str(e):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            raise e
    except Exception as e:
        # qdrant client sometimes raises ValueError or other exceptions if collection not found
        try:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
        except Exception:
            pass

    return client


def add_chunks(chunks: List[Dict[str, Any]]) -> int:
    if not chunks:
        return 0

    client = _get_client()
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    points = []
    for i, c in enumerate(chunks):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings[i],
                payload={
                    "text": c["text"],
                    "source": c["source"],
                    "source_type": c["source_type"],
                    "chunk_index": c["chunk_index"],
                    "total_chunks": c["total_chunks"],
                    "original_text": c.get("original_text", c["text"]),
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )
    return len(chunks)


def list_sources() -> List[Dict[str, Any]]:
    client = _get_client()
    
    seen: Dict[str, Dict] = {}
    
    # Simple scroll to collect sources
    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
            offset=offset
        )
        
        for record in records:
            meta = record.payload
            if not meta:
                continue
            src = meta.get("source")
            if not src:
                continue
                
            if src not in seen:
                seen[src] = {"source": src, "source_type": meta.get("source_type"), "chunk_count": 0}
            seen[src]["chunk_count"] += 1
            
        if next_offset is None:
            break
        offset = next_offset

    return list(seen.values())


def delete_source(source: str) -> int:
    client = _get_client()
    
    # Count before deleting
    count_result = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=models.Filter(
            must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
        )
    )
    deleted_count = count_result.count
    
    if deleted_count > 0:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.Filter(
                must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
            )
        )
        
    return deleted_count


def get_total_docs() -> int:
    client = _get_client()
    return client.count(collection_name=COLLECTION_NAME).count


def search(query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    
    query_filter = None
    if where:
        # where dict from chroma looked like: {"source": {"$in": [...]}}
        # We need to map it to Qdrant Filter
        must_conditions = []
        for key, val in where.items():
            if isinstance(val, dict) and "$in" in val:
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=val["$in"])
                    )
                )
            else:
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=val)
                    )
                )
        if must_conditions:
            query_filter = models.Filter(must=must_conditions)

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embed_texts([query])[0],
        limit=top_k,
        query_filter=query_filter,
        with_payload=True
    )

    return [
        {
            "text": r.payload.get("text"),
            "original_text": r.payload.get("original_text", r.payload.get("text")),
            "source": r.payload.get("source"),
            "source_type": r.payload.get("source_type"),
            "chunk_index": r.payload.get("chunk_index"),
            "score": r.score,
        }
        for r in results
    ]
