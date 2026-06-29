from fastapi import APIRouter, HTTPException

from app.api.models import AgentRunRequest, AgentRunResponse
from app.agents.agent import run_agent
from app.agents.memory import create_session, list_sessions, clear_session

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def agent_run(request: AgentRunRequest):
    try:
        result = run_agent(
            user_message=request.message,
            model=request.model,
            max_iterations=request.max_iterations,
            session_id=request.session_id,
        )
        return AgentRunResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def new_session():
    session_id = create_session()
    return {"session_id": session_id}


@router.get("/sessions")
async def get_sessions():
    return list_sessions()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    deleted = clear_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}
