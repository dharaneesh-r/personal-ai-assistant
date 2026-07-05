import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from groq import Groq

from app.config import settings
from app.api.models import ChatRequest, ChatResponse, StatusResponse

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
    "chart (in Mermaid format) or table based on the context of the conversation."
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    client = _get_client()
    try:
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        if request.history:
            for turn in request.history:
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": request.prompt})

        completion = client.chat.completions.create(
            messages=messages,
            model=request.model,
        )
        return ChatResponse(
            response=completion.choices[0].message.content,
            model=request.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    client = _get_client()

    def generate():
        try:
            messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
            if request.history:
                for turn in request.history:
                    messages.append({"role": turn.role, "content": turn.content})
            messages.append({"role": "user", "content": request.prompt})

            stream = client.chat.completions.create(
                messages=messages,
                model=request.model,
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
async def status():
    return StatusResponse(
        groq_api_key=bool(settings.groq_api_key),
        default_model=settings.default_model,
    )
