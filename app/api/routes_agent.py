from fastapi import APIRouter, HTTPException, Request

from app.api.models import AgentRunRequest, AgentRunResponse
from app.agents.agent import run_agent
from app.agents.memory import create_session, list_sessions, clear_session
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
@limiter.limit(f"{settings.rate_limit_agent}/minute")
async def agent_run(request: Request, agent_request: AgentRunRequest):
    try:
        result = run_agent(
            user_message=agent_request.message,
            model=agent_request.model,
            max_iterations=agent_request.max_iterations,
            session_id=agent_request.session_id,
        )
        return AgentRunResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def new_session(request: Request):
    session_id = create_session()
    return {"session_id": session_id}


@router.get("/sessions")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def get_sessions(request: Request):
    return list_sessions()


@router.delete("/session/{session_id}")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def delete_session(request: Request, session_id: str):
    deleted = clear_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}
