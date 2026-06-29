import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes_agent import router as agent_router
from app.api.routes_chat import router as chat_router
from app.api.routes_eval import router as eval_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_rag import router as rag_router
from app.auth import verify_api_key
from app.config import settings
from app.logger import LoggingMiddleware, logger

os.makedirs("logs", exist_ok=True)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Groq AI Workspace")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(LoggingMiddleware)

_deps = [Depends(verify_api_key)]

app.include_router(chat_router, dependencies=_deps)
app.include_router(ingest_router, dependencies=_deps)
app.include_router(rag_router, dependencies=_deps)
app.include_router(agent_router, dependencies=_deps)
app.include_router(eval_router, dependencies=_deps)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("app/static/index.html")
