# Groq AI Workspace

A production-grade, end-to-end AI application built on **FastAPI** and **Groq**. Features a chat interface, document ingestion pipeline, RAG (Retrieval-Augmented Generation), a tool-calling agent, and LLM-based evaluation — all in a single deployable service.

## Features

- **Chat** — streaming and non-streaming LLM chat via Groq
- **Document Ingestion** — upload PDF, DOCX, TXT files or paste a URL to index into the knowledge base
- **RAG Pipeline** — hybrid semantic + BM25 retrieval with optional cross-encoder reranking
- **Agent** — Groq function-calling agent with tools: `rag_lookup`, `calculator`, `search_internet`, `run_python`
- **Evaluation** — LLM-as-judge scoring for faithfulness, relevance, and groundedness
- **Rate limiting** — per-IP limits on all endpoints
- **API key auth** — optional bearer token to secure endpoints

## Tech Stack

| Layer | Choice |
|-------|--------|
| Web framework | FastAPI + Uvicorn |
| LLM | Groq (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (runs locally) |
| Vector DB | ChromaDB (local persistent storage) |
| Hybrid search | Semantic + BM25 (`rank-bm25`) |
| Reranker | `sentence-transformers` CrossEncoder |
| Document loaders | PyPDF2, python-docx, BeautifulSoup4 |
| Config | `pydantic-settings` |
| Rate limiting | `slowapi` |

## Project Structure

```
app/
├── main.py               # FastAPI app — mounts all routers
├── config.py             # Pydantic Settings — single source of truth for env vars
├── auth.py               # Optional API key authentication
├── logger.py             # Loguru structured logging + middleware
├── api/
│   ├── models.py         # All Pydantic request/response models
│   ├── routes_chat.py    # POST /chat, POST /chat/stream, GET /chat/status
│   ├── routes_ingest.py  # POST /ingest/text, /ingest/file, /ingest/url
│   ├── routes_rag.py     # POST /rag/query, GET /rag/sources, DELETE /rag/sources
│   ├── routes_agent.py   # POST /agent/run
│   └── routes_eval.py    # POST /eval/run, POST /eval/batch
├── rag/
│   ├── embeddings.py     # Sentence-transformer embedding wrapper
│   ├── vectorstore.py    # ChromaDB read/write helpers
│   ├── retriever.py      # Semantic search — top-k chunks with metadata
│   ├── hybrid.py         # BM25 + semantic fusion
│   ├── reranker.py       # CrossEncoder reranking
│   └── pipeline.py       # Retrieve → prompt → generate
├── ingestion/
│   ├── loader.py         # PDF, TXT, DOCX, URL loaders
│   ├── chunker.py        # Recursive text splitting
│   └── processor.py      # Metadata tagging, dedup, preprocessing
├── agents/
│   ├── agent.py          # Groq tool-calling loop
│   ├── tools.py          # Tool definitions and implementations
│   └── memory.py         # Per-session conversation history
└── eval/
    └── evaluator.py      # LLM-as-judge evaluation
data/
├── raw/                  # Original uploaded documents
├── chroma_db/            # ChromaDB persistent storage (gitignored)
└── uploads/              # Temp storage for API file uploads
```

## Setup

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com)

### Local Development

```powershell
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ai-learning.git
cd ai-learning

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

```powershell
# Run the dev server
uvicorn app.main:app --reload --port 8080
```

- Chat UI: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Your Groq API key |
| `API_KEY` | No | `""` | Bearer token to secure all endpoints (leave empty to disable auth) |
| `DEFAULT_MODEL` | No | `llama-3.1-8b-instant` | Default Groq model |
| `CHROMA_DB_PATH` | No | `./data/chroma_db` | Path for ChromaDB storage |
| `EMBED_MODEL` | No | `all-MiniLM-L6-v2` | Sentence-transformer model name |
| `RATE_LIMIT_DEFAULT` | No | `60` | Requests/minute for most endpoints |
| `RATE_LIMIT_AGENT` | No | `10` | Requests/minute for the agent endpoint |

## API Endpoints

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Single LLM response |
| `POST` | `/chat/stream` | Server-sent events streaming |
| `GET` | `/chat/status` | Check API key and default model |

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain transformers in one paragraph"}'
```

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/text` | Index raw text |
| `POST` | `/ingest/file` | Upload a file (PDF, DOCX, TXT) |
| `POST` | `/ingest/url` | Fetch and index a web page |

```bash
# Upload a PDF
curl -X POST http://localhost:8080/ingest/file \
  -F "file=@document.pdf"

# Index a URL
curl -X POST http://localhost:8080/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### RAG

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/rag/query` | Retrieve + generate answer |
| `GET` | `/rag/sources` | List all indexed documents |
| `DELETE` | `/rag/sources?source=name` | Remove a document |
| `DELETE` | `/rag/sources/all` | Clear the entire index |
| `POST` | `/rag/debug` | Inspect retrieval scores |

```bash
curl -X POST http://localhost:8080/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings?",
    "top_k": 4,
    "use_hybrid": true,
    "use_rerank": true
  }'
```

### Agent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agent/run` | Run the tool-calling agent |

Available tools: `rag_lookup`, `calculator`, `search_internet`, `run_python`

```bash
curl -X POST http://localhost:8080/agent/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Search the knowledge base for the quarterly results and summarize them"}'
```

### Evaluation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/eval/run` | Score a single Q&A against context |
| `POST` | `/eval/batch` | Score multiple Q&A pairs |

Scores **faithfulness**, **relevance**, and **groundedness** on a 1–5 scale using an LLM judge.

## Deploy to Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
3. Select your repository (Railway auto-detects the Dockerfile)
4. Add environment variables in **Variables** tab:
   - `GROQ_API_KEY` — required
   - `API_KEY` — recommended for production
   - `CHROMA_DB_PATH` — set to `/app/data/chroma_db`
5. Railway assigns a public URL automatically

> **Note:** ChromaDB uses local disk storage inside the container. Data is lost on redeploy. For persistent storage, swap ChromaDB for [Qdrant Cloud](https://qdrant.tech) (free tier available).

## Docker

```bash
# Build
docker build -t groq-ai-workspace .

# Run
docker run -p 8000:8000 --env-file .env groq-ai-workspace
```

## Authentication

When `API_KEY` is set in `.env`, all endpoints require a bearer token:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

Leave `API_KEY` empty to disable authentication.
