# AI Learning — End-to-End AI Application

## Project Goal
Build a production-grade, end-to-end AI application on top of FastAPI and Groq. Features are added incrementally: starting from a basic LLM chat, then adding document ingestion, vector search, RAG pipelines, and autonomous agents.

## Current State
| File | Purpose |
|------|---------|
| `app/main.py` | Working Groq chat UI — FastAPI backend + single-file HTML frontend |
| `.env` | `GROQ_API_KEY` configured |
| `.venv/` | Python 3.11 virtual environment |

## Target Architecture
```
app/
├── main.py              # FastAPI app factory + mounts all routers
├── config.py            # Pydantic Settings — reads .env, single source of truth
├── api/
│   ├── routes_chat.py   # /chat  — basic LLM chat (existing logic, refactored)
│   ├── routes_rag.py    # /rag   — RAG query endpoint
│   ├── routes_ingest.py # /ingest — upload & index documents
│   └── models.py        # All Pydantic request/response models
├── rag/
│   ├── embeddings.py    # Embedding model wrapper (sentence-transformers)
│   ├── vectorstore.py   # ChromaDB read/write helpers
│   ├── retriever.py     # Semantic search — returns top-k chunks with metadata
│   └── pipeline.py      # Compose retrieve + prompt + generate into one call
├── ingestion/
│   ├── loader.py        # Source loaders: PDF, TXT, DOCX, URL, directory
│   ├── chunker.py       # Text splitting: recursive, sentence, token-based
│   └── processor.py     # Metadata tagging, dedup, preprocessing
├── agents/
│   ├── agent.py         # Groq tool-calling agent loop
│   └── tools.py         # Tool definitions: web_search, calculator, rag_lookup
data/
├── raw/                 # Original uploaded documents
├── chroma_db/           # ChromaDB persistent storage (gitignored)
└── uploads/             # Temp storage for API file uploads
tests/
├── test_rag.py
├── test_ingestion.py
└── test_agents.py
```

## Tech Stack
| Layer | Choice | Notes |
|-------|--------|-------|
| Web framework | FastAPI + Uvicorn | async-first |
| LLM | Groq | llama-3.1-8b-instant (fast), llama-3.3-70b-versatile (capable) |
| Embeddings | `sentence-transformers` | `all-MiniLM-L6-v2` — runs locally, no API key |
| Vector DB | ChromaDB | local default; swap to Qdrant for production |
| Document loading | PyPDF2, python-docx, BeautifulSoup4 | per file type |
| Agent tools | Groq function-calling API | no LangChain dependency |
| Config | `pydantic-settings` | validates env vars at startup |

## Environment Variables (`.env`)
```
GROQ_API_KEY=...          # required
CHROMA_DB_PATH=./data/chroma_db   # optional, has default
EMBED_MODEL=all-MiniLM-L6-v2      # optional, has default
```

## How to Run
```powershell
# activate venv
.venv\Scripts\activate

# install all deps
pip install -r requirements.txt

# run dev server (auto-reload)
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` for the chat UI.
Open `http://localhost:8000/docs` for the interactive API docs.

## Build Order (incremental)
1. **Config module** — `app/config.py` with pydantic-settings
2. **Refactor main.py** — extract Groq logic into `app/api/routes_chat.py`
3. **Ingestion pipeline** — loader → chunker → processor
4. **Vector store** — ChromaDB setup, embed + store chunks
5. **Retriever** — semantic search over stored chunks
6. **RAG pipeline** — retriever + prompt template + Groq generate
7. **Agents** — tool-calling loop with rag_lookup + web_search tools
8. **Frontend upgrades** — add RAG toggle, file upload UI, agent chat mode

## Coding Conventions
- All new modules go under `app/` as packages (include `__init__.py`)
- API endpoints live in `app/api/routes_*.py`, mounted in `app/main.py`
- All settings read from `app/config.py` — never `os.environ.get()` inline
- Pydantic models for every request and response body
- Async (`async def`) for all FastAPI route handlers
- Sync functions for CPU-bound work (embeddings, chunking)
- No LangChain unless a feature genuinely needs it — prefer direct API calls
- `data/chroma_db/` and `data/uploads/` are gitignored

## Key API Endpoints (planned)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Basic LLM chat (current `/generate`) |
| POST | `/ingest/file` | Upload a file, chunk and embed it |
| POST | `/ingest/url` | Ingest a URL |
| POST | `/rag/query` | RAG query — retrieve + generate |
| GET  | `/rag/sources` | List all indexed documents |
| DELETE | `/rag/source/{id}` | Remove a document from the index |
| POST | `/agent/run` | Run the tool-calling agent |
