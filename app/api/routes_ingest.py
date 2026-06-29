from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.api.models import ChunkPreview, IngestResponse, IngestTextRequest, IngestUrlRequest
from app.ingestion.loader import load_file, load_url
from app.ingestion.processor import process_document
from app.rag.vectorstore import add_chunks

router = APIRouter(prefix="/ingest", tags=["ingestion"])

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


@router.post("/text", response_model=IngestResponse)
async def ingest_text(request: IngestTextRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    chunks = process_document(request.text, source=request.source_name, source_type="text")
    stored = add_chunks(chunks)
    return _build_response(request.source_name, "text", chunks, stored)


@router.post("/file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)):
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
    return _build_response(file.filename, source_type, chunks, stored)


@router.post("/url", response_model=IngestResponse)
async def ingest_url(request: IngestUrlRequest):
    try:
        text = load_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content found at the given URL.")

    chunks = process_document(text, source=request.url, source_type="url")
    stored = add_chunks(chunks)
    return _build_response(request.url, "url", chunks, stored)


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
