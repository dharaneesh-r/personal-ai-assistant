Add support for a new document source type to the ingestion pipeline.

The user will specify the source type: PDF, DOCX, TXT, URL, or directory scan.

Steps:
1. Read `app/ingestion/loader.py` to see what loaders already exist.
2. Add the new loader class/function — do not modify existing loaders.
3. Read `app/ingestion/chunker.py` and choose or add an appropriate chunking strategy for this source type (PDFs often need larger chunks; web pages need HTML stripping first).
4. Read `app/ingestion/processor.py` and ensure metadata is tagged correctly (source_type, source_path, created_at, chunk_index).
5. Read `app/api/routes_ingest.py` (or create it if missing) and add or update the relevant endpoint.
6. Mount the ingest router in `app/main.py` if not already done.
7. Update `requirements.txt` with any new dependency needed (e.g. `PyPDF2` for PDF, `python-docx` for DOCX, `beautifulsoup4` for URL).

Constraints:
- Chunk size default: 512 tokens, overlap: 50 tokens.
- Each chunk stored in ChromaDB must have metadata: `source`, `source_type`, `chunk_index`, `total_chunks`.
- Never delete existing collections in ChromaDB — only upsert.
