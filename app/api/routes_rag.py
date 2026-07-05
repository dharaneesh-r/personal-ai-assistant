from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.models import DeleteResponse, RagQueryRequest, RagQueryResponse, SourceInfo
from app.rag.pipeline import rag_query
from app.rag.retriever import retrieve
from app.rag.vectorstore import delete_source, list_sources, _get_collection
from app.rag.graphstore import delete_source_graph, clear_graph, get_all_graph

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest):
    try:
        history = [(t.user, t.assistant) for t in request.history] if request.history else None
        result = rag_query(
            question=request.question,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            model=request.model,
            source_filter=request.source_filter,
            use_hybrid=request.use_hybrid,
            use_rerank=request.use_rerank,
            rewrite_query=request.rewrite_query,
            use_graph=request.use_graph,
            history=history,
        )
        return RagQueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[SourceInfo])
async def get_sources():
    return list_sources()


@router.delete("/sources", response_model=DeleteResponse)
async def remove_source(source: str = Query(..., description="Exact source name or URL to delete")):
    deleted = delete_source(source)
    delete_source_graph(source)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found in vector store.")
    return DeleteResponse(source=source, chunks_deleted=deleted)


@router.delete("/sources/all")
async def clear_all_sources():
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
async def debug_retrieval(request: DebugRequest) -> Dict[str, Any]:
    try:
        chunks = retrieve(
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            use_hybrid=request.use_hybrid,
            use_rerank=request.use_rerank,
        )
        total_docs = _get_collection().count()
        return {
            "query": request.query,
            "total_chunks_in_db": total_docs,
            "retrieved": len(chunks),
            "settings": {
                "top_k": request.top_k,
                "score_threshold": request.score_threshold,
                "use_hybrid": request.use_hybrid,
                "use_rerank": request.use_rerank,
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
async def get_graph():
    try:
        return get_all_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/graph/clear")
async def delete_graph():
    try:
        clear_graph()
        return {"status": "success", "message": "Knowledge graph cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
