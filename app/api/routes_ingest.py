from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from app.api.models import ChunkPreview, IngestResponse, IngestTextRequest, IngestUrlRequest
from app.ingestion.loader import load_file, load_url
from app.ingestion.processor import process_document
from app.rag.vectorstore import add_chunks
from app.ingestion.graph_extractor import extract_graph_from_text
from app.rag.graphstore import add_entities_and_relations
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/ingest", tags=["ingestion"])

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def _extract_and_store_graph(text: str, source: str):
    graph = extract_graph_from_text(text)
    if graph["entities"] or graph["relations"]:
        add_entities_and_relations(graph["entities"], graph["relations"], source)


@router.post("/text", response_model=IngestResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def ingest_text(request: Request, ingest_request: IngestTextRequest):
    if not ingest_request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    chunks = process_document(ingest_request.text, source=ingest_request.source_name, source_type="text")
    stored = add_chunks(chunks)
    _extract_and_store_graph(ingest_request.text, ingest_request.source_name)
    return _build_response(ingest_request.source_name, "text", chunks, stored)


@router.post("/file", response_model=IngestResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def ingest_file(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported: .txt, .pdf, .docx",
        )

    dest = UPLOADS_DIR / file.filename
    dest.write_bytes(await file.read())

    try:
        text = load_file(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    source_type = suffix.lstrip(".")
    chunks = process_document(text, source=file.filename, source_type=source_type)
    stored = add_chunks(chunks)
    _extract_and_store_graph(text, file.filename)
    return _build_response(file.filename, source_type, chunks, stored)


@router.post("/url", response_model=IngestResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def ingest_url(request: Request, ingest_request: IngestUrlRequest):
    try:
        text = load_url(ingest_request.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content found at the given URL.")

    chunks = process_document(text, source=ingest_request.url, source_type="url")
    stored = add_chunks(chunks)
    _extract_and_store_graph(text, ingest_request.url)
    return _build_response(ingest_request.url, "url", chunks, stored)


def _build_response(source: str, source_type: str, chunks: list, stored: int) -> IngestResponse:
    return IngestResponse(
        source=source,
        source_type=source_type,
        chunks_created=len(chunks),
        chunks_stored=stored,
        preview=[
            ChunkPreview(
                chunk_index=c["chunk_index"],
                text_preview=c["text"][:150] + "..." if len(c["text"]) > 150 else c["text"],
                char_count=len(c["text"]),
            )
            for c in chunks[:3]
        ],
    )
