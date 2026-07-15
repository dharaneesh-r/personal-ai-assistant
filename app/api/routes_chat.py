import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from groq import Groq

from app.config import settings
from app.api.models import ChatRequest, ChatResponse, StatusResponse
from app.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_client() -> Groq:
    if not settings.groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set in .env")
    return Groq(api_key=settings.groq_api_key)


_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Be extremely forgiving of spelling mistakes, typos, "
    "and grammatical errors. Intelligently deduce the user's intent and answer directly "
    "instead of asking for minor clarifications. If the user asks for a chart or table "
    "(even with typos like 'piechart ot fhtat' or 'table ot thta'), output the requested "
    "chart (in Mermaid format) or table based on the context of the conversation. "
    "IMPORTANT: When generating Mermaid charts, you MUST obey these syntax rules:\n"
    "1. Node IDs (variable names) must be strictly single alphanumeric words without spaces, dots, or special characters. Use snake_case (e.g. dharaneesh_r or node_js).\n"
    "2. Always enclose node labels in double quotes (e.g., dharaneesh_r[\"Dharaneesh R\"] or node_js[\"Node.js\"]).\n"
    "3. Links with text must be formatted as: A -->|text| B (do NOT write A -->|text|> B).\n"
    "Example of correct code:\n"
    "graph TB\n"
    "    dharaneesh[\"Dharaneesh R\"] -->|Skills| node_js[\"Node.js\"]"
)


@router.post("", response_model=ChatResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def chat(request: Request, chat_request: ChatRequest):
    client = _get_client()
    try:
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        if chat_request.history:
            for turn in chat_request.history:
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": chat_request.prompt})

        completion = client.chat.completions.create(
            messages=messages,
            model=chat_request.model,
        )
        return ChatResponse(
            response=completion.choices[0].message.content,
            model=chat_request.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def chat_stream(request: Request, chat_request: ChatRequest):
    client = _get_client()

    def generate():
        try:
            messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
            if chat_request.history:
                for turn in chat_request.history:
                    messages.append({"role": turn.role, "content": turn.content})
            messages.append({"role": "user", "content": chat_request.prompt})

            stream = client.chat.completions.create(
                messages=messages,
                model=chat_request.model,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/status", response_model=StatusResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def status(request: Request):
    return StatusResponse(
        groq_api_key=bool(settings.groq_api_key),
        default_model=settings.default_model,
    )
