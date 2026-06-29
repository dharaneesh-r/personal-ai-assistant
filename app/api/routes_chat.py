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


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    client = _get_client()
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": request.prompt}],
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
            stream = client.chat.completions.create(
                messages=[{"role": "user", "content": request.prompt}],
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
