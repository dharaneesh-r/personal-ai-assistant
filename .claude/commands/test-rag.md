Run a quick end-to-end test of the RAG pipeline and report the result.

Steps:
1. Check that the FastAPI server is not already running on port 8000.
2. Start the server in the background: `uvicorn app.main:app --port 8000`
3. Wait 2 seconds for startup.
4. POST a test ingest request:
   - If a file exists in `data/raw/`, use it.
   - Otherwise create a small test document `data/raw/test.txt` with 3–4 paragraphs of varied content.
5. POST to `/ingest/file` (or `/ingest/text` if that's what exists) with the test document.
6. POST to `/rag/query` with a question that should be answerable from the test document.
7. Print the retrieved chunks and the generated answer.
8. Report:
   - Number of chunks indexed
   - Top retrieved chunk (with similarity score if available)
   - LLM answer
   - Any errors encountered
9. Stop the background server.

If any endpoint doesn't exist yet, report which modules are missing and stop — do not create stubs.
