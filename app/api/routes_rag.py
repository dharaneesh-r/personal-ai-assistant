from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.models import DeleteResponse, RagQueryRequest, RagQueryResponse, SourceInfo
from app.rag.pipeline import rag_query
from app.rag.retriever import retrieve
from app.rag.vectorstore import delete_source, list_sources, _get_collection
from app.rag.graphstore import delete_source_graph, clear_graph, get_all_graph
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def query_rag(request: Request, rag_request: RagQueryRequest):
    try:
        history = [(t.user, t.assistant) for t in rag_request.history] if rag_request.history else None
        result = rag_query(
            question=rag_request.question,
            top_k=rag_request.top_k,
            score_threshold=rag_request.score_threshold,
            model=rag_request.model,
            source_filter=rag_request.source_filter,
            use_hybrid=rag_request.use_hybrid,
            use_rerank=rag_request.use_rerank,
            rewrite_query=rag_request.rewrite_query,
            use_graph=rag_request.use_graph,
            history=history,
        )
        return RagQueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[SourceInfo])
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_sources(request: Request):
    return list_sources()


@router.delete("/sources", response_model=DeleteResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def remove_source(request: Request, source: str = Query(..., description="Exact source name or URL to delete")):
    deleted = delete_source(source)
    delete_source_graph(source)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found in vector store.")
    return DeleteResponse(source=source, chunks_deleted=deleted)


@router.delete("/sources/all")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def clear_all_sources(request: Request):
    sources = list_sources()
    total = 0
    for s in sources:
        total += delete_source(s["source"])
    clear_graph()
    return {"deleted_sources": len(sources), "deleted_chunks": total}


class DebugRequest(BaseModel):
    query: str
    top_k: int = 8
    score_threshold: float = 0.0
    use_hybrid: bool = True
    use_rerank: bool = False


@router.post("/debug")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def debug_retrieval(request: Request, debug_request: DebugRequest) -> Dict[str, Any]:
    try:
        chunks = retrieve(
            query=debug_request.query,
            top_k=debug_request.top_k,
            score_threshold=debug_request.score_threshold,
            use_hybrid=debug_request.use_hybrid,
            use_rerank=debug_request.use_rerank,
        )
        total_docs = _get_collection().count()
        return {
            "query": debug_request.query,
            "total_chunks_in_db": total_docs,
            "retrieved": len(chunks),
            "settings": {
                "top_k": debug_request.top_k,
                "score_threshold": debug_request.score_threshold,
                "use_hybrid": debug_request.use_hybrid,
                "use_rerank": debug_request.use_rerank,
            },
            "chunks": [
                {
                    "rank": i + 1,
                    "score": c.get("score", 0),
                    "rerank_score": c.get("rerank_score"),
                    "source": c["source"],
                    "source_type": c["source_type"],
                    "text_preview": c["text"][:200] + ("..." if len(c["text"]) > 200 else ""),
                    "text_length": len(c["text"]),
                }
                for i, c in enumerate(chunks)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_graph(request: Request):
    try:
        return get_all_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/graph/clear")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def delete_graph(request: Request):
    try:
        clear_graph()
        return {"status": "success", "message": "Knowledge graph cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
