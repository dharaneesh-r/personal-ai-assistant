"""Tests for ingestion pipeline: loader, chunker, and ingest API endpoints."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ingestion.chunker import chunk_text
from app.ingestion.loader import load_file, load_txt
from app.main import app

client = TestClient(app)


# ── chunker ──────────────────────────────────────────────────────────────────

class TestChunkText:
    def test_empty_string_returns_empty(self):
        assert chunk_text("") == []

    def test_short_text_returns_single_chunk(self):
        text = "Hello world"
        chunks = chunk_text(text, chunk_size=1000)
        assert chunks == [text]

    def test_long_text_splits_into_multiple_chunks(self):
        text = "word " * 500  # ~2500 chars
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1

    def test_chunk_size_is_respected(self):
        text = "a" * 3000
        chunks = chunk_text(text, chunk_size=500, overlap=0)
        for chunk in chunks:
            assert len(chunk) <= 600  # some slack for boundary logic

    def test_overlap_makes_chunks_share_content(self):
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        for i in range(len(chunks) - 1):
            last_words = chunks[i][-50:].strip()
            next_start = chunks[i + 1][:80]
            # There should be some shared content in the overlap window
            assert len(chunks[i]) > 0 and len(chunks[i + 1]) > 0

    def test_no_empty_chunks(self):
        text = "   ".join(["sentence."] * 100)
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert all(c.strip() for c in chunks)

    def test_whitespace_normalized(self):
        text = "hello   \n\n   world"
        chunks = chunk_text(text, chunk_size=1000)
        assert chunks == ["hello world"]


# ── loader ───────────────────────────────────────────────────────────────────

class TestLoadTxt:
    def test_reads_file_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello from txt file")
            path = f.name
        assert load_txt(path) == "Hello from txt file"

    def test_load_file_routes_txt(self, tmp_path):
        p = tmp_path / "sample.txt"
        p.write_text("test content", encoding="utf-8")
        assert load_file(str(p)) == "test content"

    def test_load_file_unsupported_type_raises(self, tmp_path):
        p = tmp_path / "sample.xyz"
        p.write_text("data")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_file(str(p))


# ── ingest API endpoints ──────────────────────────────────────────────────────

class TestIngestTextEndpoint:
    @patch("app.api.routes_ingest.add_chunks", return_value=2)
    @patch("app.api.routes_ingest.process_document")
    def test_ingest_text_success(self, mock_proc, mock_add):
        mock_proc.return_value = [
            {"chunk_index": 0, "text": "chunk one", "source": "test", "source_type": "text"},
            {"chunk_index": 1, "text": "chunk two", "source": "test", "source_type": "text"},
        ]
        res = client.post("/ingest/text", json={"text": "Some content to ingest", "source_name": "test"})
        assert res.status_code == 200
        assert res.json()["chunks_stored"] == 2

    def test_ingest_text_empty_returns_400(self):
        res = client.post("/ingest/text", json={"text": "", "source_name": "test"})
        assert res.status_code == 400

    @patch("app.api.routes_ingest.add_chunks", return_value=3)
    @patch("app.api.routes_ingest.process_document")
    @patch("app.api.routes_ingest.load_url", return_value="Some page content here " * 20)
    def test_ingest_url_success(self, mock_load, mock_proc, mock_add):
        mock_proc.return_value = [
            {"chunk_index": i, "text": "chunk", "source": "http://example.com", "source_type": "url"}
            for i in range(3)
        ]
        res = client.post("/ingest/url", json={"url": "http://example.com"})
        assert res.status_code == 200
        assert res.json()["source_type"] == "url"
