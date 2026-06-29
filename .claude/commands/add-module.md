Scaffold a new module in this AI application.

The user will specify which module to add. Valid modules:

- **config** — `app/config.py` using pydantic-settings
- **ingestion** — `app/ingestion/` (loader, chunker, processor)
- **vectorstore** — `app/rag/vectorstore.py` with ChromaDB
- **embeddings** — `app/rag/embeddings.py` with sentence-transformers
- **retriever** — `app/rag/retriever.py` semantic search
- **rag-pipeline** — `app/rag/pipeline.py` full RAG compose
- **agents** — `app/agents/` (agent loop + tools)
- **routes** — a new `app/api/routes_<name>.py` and mount it in main.py

Steps:
1. Read `CLAUDE.md` to confirm the target architecture.
2. Read any existing related files before creating new ones to avoid duplication.
3. Create the module file(s) with proper `__init__.py`.
4. If the module adds API routes, mount the router in `app/main.py`.
5. If new dependencies are needed, append them to `requirements.txt` (create it if missing).
6. Keep each function focused — no mega-functions.
7. Use `app/config.py` (Settings) for all env vars — never `os.environ.get()` directly.
8. Add async route handlers in FastAPI routes; keep CPU-bound work (embeddings, chunking) in sync helpers.

Do not install packages — only update requirements.txt. The user will install.
