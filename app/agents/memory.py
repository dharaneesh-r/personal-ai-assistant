from typing import Any, Dict, List
import uuid

# In-memory session store: session_id -> list of {role, content}
_sessions: Dict[str, List[Dict[str, str]]] = {}


def create_session() -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = []
    return session_id


def get_history(session_id: str) -> List[Dict[str, str]]:
    return _sessions.get(session_id, [])


def append_turn(session_id: str, user: str, assistant: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({"role": "user", "content": user})
    _sessions[session_id].append({"role": "assistant", "content": assistant})


def clear_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def list_sessions() -> List[Dict[str, Any]]:
    return [
        {"session_id": sid, "turns": len(msgs) // 2}
        for sid, msgs in _sessions.items()
    ]
