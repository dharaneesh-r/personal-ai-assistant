from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.database import (
    save_session,
    get_all_sessions,
    get_session,
    delete_session,
    save_message,
    get_session_messages,
    save_evaluation,
    get_all_evaluations
)
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/history", tags=["history"])

# --- Models ---

class SessionModel(BaseModel):
    id: str
    title: str
    mode: str
    model: str
    created_at: str

class MessageModel(BaseModel):
    id: str
    role: str
    content: str
    mode: str
    timestamp: str
    sources: Optional[List[str]] = None
    chunks_used: Optional[int] = None
    rewritten_query: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    iterations: Optional[int] = None
    model: Optional[str] = None

class EvaluationModel(BaseModel):
    id: str
    question: str
    answer: str
    context: str
    overall: float
    faithfulness_score: int
    faithfulness_reason: str
    relevance_score: int
    relevance_reason: str
    groundedness_score: int
    groundedness_reason: str
    model: str
    timestamp: str

# --- Endpoints ---

@router.get("/chats")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_chats(request: Request):
    try:
        return get_all_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chats/{session_id}")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_chat_detail(request: Request, session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_session_messages(session_id)
    return {
        "session": session,
        "messages": messages
    }

@router.post("/chats")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def create_or_update_session(request: Request, payload: SessionModel):
    try:
        save_session(
            session_id=payload.id,
            title=payload.title,
            mode=payload.mode,
            model=payload.model,
            created_at=payload.created_at
        )
        return {"status": "ok", "id": payload.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chats/{session_id}/message")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def append_chat_message(request: Request, session_id: str, payload: MessageModel):
    try:
        save_message(
            msg_id=payload.id,
            session_id=session_id,
            role=payload.role,
            content=payload.content,
            mode=payload.mode,
            timestamp=payload.timestamp,
            sources=payload.sources,
            chunks_used=payload.chunks_used,
            rewritten_query=payload.rewritten_query,
            tool_calls=payload.tool_calls,
            iterations=payload.iterations,
            model=payload.model
        )
        return {"status": "ok", "id": payload.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/chats/{session_id}")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def delete_chat_session(request: Request, session_id: str):
    try:
        delete_session(session_id)
        return {"status": "ok", "id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluations")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def create_evaluation_record(request: Request, payload: EvaluationModel):
    try:
        save_evaluation(
            eval_id=payload.id,
            question=payload.question,
            answer=payload.answer,
            context=payload.context,
            overall=payload.overall,
            faithfulness_score=payload.faithfulness_score,
            faithfulness_reason=payload.faithfulness_reason,
            relevance_score=payload.relevance_score,
            relevance_reason=payload.relevance_reason,
            groundedness_score=payload.groundedness_score,
            groundedness_reason=payload.groundedness_reason,
            model=payload.model,
            timestamp=payload.timestamp
        )
        return {"status": "ok", "id": payload.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluations")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_evaluations_history(request: Request):
    try:
        return get_all_evaluations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
