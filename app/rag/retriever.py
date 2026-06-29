from typing import Any, Dict, List, Optional

from app.rag.vectorstore import search
from app.rag.hybrid import hybrid_search
from app.rag.reranker import rerank


def retrieve(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    source_filter: Optional[str] = None,
    use_hybrid: bool = False,
    use_rerank: bool = False,
) -> List[Dict[str, Any]]:
    if use_hybrid:
        results = hybrid_search(query, top_k=top_k * 2)
    else:
        results = search(query, top_k=top_k * 2 if use_rerank else top_k)

    # RRF scores (hybrid) are tiny (~0.016) — threshold only applies to cosine similarity
    if score_threshold > 0.0 and not use_hybrid:
        results = [r for r in results if r.get("score", 0) >= score_threshold]

    if source_filter:
        results = [r for r in results if r["source"] == source_filter]

    if use_rerank:
        results = rerank(query, results, top_k=top_k)
    else:
        results = results[:top_k]

    return results
