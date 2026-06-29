Show the current build status of the end-to-end AI application and what to build next.

Steps:
1. Read `CLAUDE.md` for the target architecture.
2. Check which files exist across the planned structure:
   - `app/config.py`
   - `app/api/routes_chat.py`, `routes_rag.py`, `routes_ingest.py`, `models.py`
   - `app/rag/embeddings.py`, `vectorstore.py`, `retriever.py`, `pipeline.py`
   - `app/ingestion/loader.py`, `chunker.py`, `processor.py`
   - `app/agents/agent.py`, `tools.py`
   - `requirements.txt`
   - `data/raw/`, `data/chroma_db/`
3. Print a checklist:
   - [x] file exists and is non-empty
   - [ ] file is missing or empty
4. Based on the build order in CLAUDE.md, identify the next unbuilt step.
5. Recommend the exact command to build it (e.g. `/add-module config`).

Keep the output short — checklist + one clear "next step" recommendation.
