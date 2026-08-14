from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from app.rag.vectorstore import search, _get_client, COLLECTION_NAME
from qdrant_client import models

def _fetch_all_docs(where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    
    query_filter = None
    if where:
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

    all_docs = []
    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
            scroll_filter=query_filter,
            offset=offset
        )
        
        for r in records:
            all_docs.append({
                "text": r.payload.get("text"),
                "source": r.payload.get("source"),
                "source_type": r.payload.get("source_type"),
                "chunk_index": r.payload.get("chunk_index"),
            })
            
        if next_offset is None:
            break
        offset = next_offset
        
    return all_docs


def _rrf(ranks: List[List[int]], k: int = 60) -> List[float]:
    n = max(max(r) for r in ranks) + 1
    scores = [0.0] * n
    for rank_list in ranks:
        for rank, idx in enumerate(rank_list):
            scores[idx] += 1.0 / (k + rank + 1)
    return scores


def hybrid_search(query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    all_docs = _fetch_all_docs(where=where)
    if not all_docs:
        return []

    # Vector search — get 2x candidates
    vector_results = search(query, top_k=min(top_k * 2, len(all_docs)), where=where)
    vector_texts = [r["text"] for r in vector_results]

    # BM25 search over all docs
    tokenized = [doc["text"].lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized)
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k * 2]
    bm25_top_docs = [all_docs[i] for i in bm25_top_indices]
    bm25_texts = [d["text"] for d in bm25_top_docs]

    # Merge candidate pool (deduplicated by text)
    seen = {}
    for doc in vector_results:
        seen[doc["text"]] = doc
    for doc in bm25_top_docs:
        if doc["text"] not in seen:
            seen[doc["text"]] = {"text": doc["text"], "source": doc["source"], "source_type": doc["source_type"], "chunk_index": doc["chunk_index"], "score": 0.0}
    pool = list(seen.values())
    pool_texts = [d["text"] for d in pool]

    # Build rank lists for RRF
    vector_ranks = [pool_texts.index(t) if t in pool_texts else len(pool) for t in vector_texts]
    bm25_ranks = [pool_texts.index(t) if t in pool_texts else len(pool) for t in bm25_texts]

    rrf_scores = _rrf([vector_ranks, bm25_ranks])

    for i, doc in enumerate(pool):
        doc["score"] = round(rrf_scores[i], 6)

    pool.sort(key=lambda d: d["score"], reverse=True)
    return pool[:top_k]
