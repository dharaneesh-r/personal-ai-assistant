from typing import List, Optional

from pydantic import BaseModel


# --- Chat ---

class ChatHistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    model: str = "llama-3.1-8b-instant"
    history: Optional[List[ChatHistoryTurn]] = None


class ChatResponse(BaseModel):
    response: str
    model: str


class StatusResponse(BaseModel):
    groq_api_key: bool
    default_model: str


# --- Ingestion ---

class IngestTextRequest(BaseModel):
    text: str
    source_name: str = "manual_input"


class IngestUrlRequest(BaseModel):
    url: str


class ChunkPreview(BaseModel):
    chunk_index: int
    text_preview: str
    char_count: int


class IngestResponse(BaseModel):
    source: str
    source_type: str
    chunks_created: int
    chunks_stored: int
    preview: List[ChunkPreview]


# --- Vector Store ---

class SourceInfo(BaseModel):
    source: str
    source_type: str
    chunk_count: int


class DeleteResponse(BaseModel):
    source: str
    chunks_deleted: int


# --- RAG ---

class HistoryTurn(BaseModel):
    user: str
    assistant: str


class RagQueryRequest(BaseModel):
    question: str
    top_k: int = 5
    score_threshold: float = 0.2
    model: str = "llama-3.1-8b-instant"
    source_filter: Optional[List[str]] = None
    use_hybrid: bool = False
    use_rerank: bool = False
    rewrite_query: bool = False
    use_graph: bool = False
    history: Optional[List[HistoryTurn]] = None


class RagQueryResponse(BaseModel):
    answer: str
    sources: List[str]
    chunks_used: int
    model: str
    rewritten_query: Optional[str] = None


# --- Agent ---

class AgentRunRequest(BaseModel):
    message: str
    model: str = "llama-3.3-70b-versatile"
    max_iterations: int = 10
    session_id: Optional[str] = None


class ToolCallRecord(BaseModel):
    tool: str
    args: dict
    result: dict


class AgentRunResponse(BaseModel):
    answer: str
    tool_calls_made: List[ToolCallRecord]
    iterations: int
    model: str
    session_id: Optional[str] = None
