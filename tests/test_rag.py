"""Tests for RAG pipeline: retriever, pipeline, and RAG API endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ingestion.chunker import chunk_text
from app.main import app
from app.rag.retriever import retrieve

client = TestClient(app)

_FAKE_CHUNKS = [
    {"text": "Dharaneesh is a software engineer.", "source": "resume.pdf", "source_type": "pdf", "score": 0.9},
    {"text": "He works on AI applications.", "source": "resume.pdf", "source_type": "pdf", "score": 0.8},
]


# ── retriever ────────────────────────────────────────────────────────────────

class TestRetrieve:
    @patch("app.rag.retriever.search")
    def test_basic_retrieval_returns_chunks(self, mock_search):
        mock_search.return_value = _FAKE_CHUNKS
        results = retrieve("Who is Dharaneesh?", top_k=2)
        assert len(results) == 2
        assert results[0]["source"] == "resume.pdf"

    @patch("app.rag.retriever.search")
    def test_score_threshold_filters_low_scores(self, mock_search):
        chunks = [
            {"text": "High score chunk", "source": "a.txt", "source_type": "txt", "score": 0.9},
            {"text": "Low score chunk", "source": "b.txt", "source_type": "txt", "score": 0.1},
        ]
        mock_search.return_value = chunks
        results = retrieve("query", top_k=5, score_threshold=0.5)
        assert all(r["score"] >= 0.5 for r in results)
        assert len(results) == 1

    @patch("app.rag.retriever.search")
    def test_source_filter_applied(self, mock_search):
        mock_search.return_value = _FAKE_CHUNKS + [
            {"text": "Unrelated", "source": "other.txt", "source_type": "txt", "score": 0.7}
        ]
        results = retrieve("query", top_k=5, source_filter="resume.pdf")
        assert all(r["source"] == "resume.pdf" for r in results)

    @patch("app.rag.retriever.hybrid_search")
    def test_hybrid_mode_uses_hybrid_search(self, mock_hybrid):
        mock_hybrid.return_value = _FAKE_CHUNKS
        results = retrieve("query", top_k=2, use_hybrid=True)
        mock_hybrid.assert_called_once()
        assert len(results) <= 2

    @patch("app.rag.retriever.search")
    @patch("app.rag.retriever.rerank")
    def test_rerank_called_when_enabled(self, mock_rerank, mock_search):
        mock_search.return_value = _FAKE_CHUNKS
        mock_rerank.return_value = [_FAKE_CHUNKS[0]]
        results = retrieve("query", top_k=1, use_rerank=True)
        mock_rerank.assert_called_once()


# ── RAG pipeline ─────────────────────────────────────────────────────────────

class TestRagPipeline:
    @patch("app.rag.pipeline.retrieve")
    @patch("app.rag.pipeline.Groq")
    def test_rag_query_returns_answer(self, mock_groq_cls, mock_retrieve):
        mock_retrieve.return_value = _FAKE_CHUNKS
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "He is a software engineer."
        mock_groq_cls.return_value.chat.completions.create.return_value = mock_completion

        from app.rag.pipeline import rag_query
        result = rag_query("Who is Dharaneesh?")

        assert result["answer"] == "He is a software engineer."
        assert result["chunks_used"] == 2
        assert "resume.pdf" in result["sources"]

    @patch("app.rag.pipeline.retrieve")
    def test_rag_query_no_chunks_returns_fallback(self, mock_retrieve):
        mock_retrieve.return_value = []

        from app.rag.pipeline import rag_query
        result = rag_query("Unknown question")

        assert result["chunks_used"] == 0
        assert "could not find" in result["answer"].lower()

    @patch("app.rag.pipeline.retrieve")
    @patch("app.rag.pipeline.Groq")
    def test_rag_query_rewrite_called_when_enabled(self, mock_groq_cls, mock_retrieve):
        mock_retrieve.return_value = _FAKE_CHUNKS
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer"
        mock_groq_cls.return_value.chat.completions.create.return_value = mock_completion

        from app.rag.pipeline import rag_query
        result = rag_query("skills?", rewrite_query=True)

        assert result["rewritten_query"] is not None


# ── RAG API endpoints ─────────────────────────────────────────────────────────

class TestRagEndpoints:
    @patch("app.api.routes_rag.rag_query")
    def test_query_endpoint_success(self, mock_rag):
        mock_rag.return_value = {
            "answer": "Test answer",
            "sources": ["doc.pdf"],
            "chunks_used": 1,
            "model": "llama-3.1-8b-instant",
            "rewritten_query": None,
        }
        res = client.post("/rag/query", json={"question": "Test question"})
        assert res.status_code == 200
        assert res.json()["answer"] == "Test answer"

    def test_query_endpoint_missing_question_returns_422(self):
        res = client.post("/rag/query", json={})
        assert res.status_code == 422

    @patch("app.api.routes_rag.list_sources")
    def test_sources_endpoint_returns_list(self, mock_list):
        mock_list.return_value = [
            {"source": "doc.pdf", "source_type": "pdf", "chunk_count": 5}
        ]
        res = client.get("/rag/sources")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    @patch("app.api.routes_rag.delete_source")
    def test_delete_source_success(self, mock_del):
        mock_del.return_value = 3
        res = client.delete("/rag/sources?source=doc.pdf")
        assert res.status_code == 200
        assert res.json()["chunks_deleted"] == 3

    @patch("app.api.routes_rag.delete_source")
    def test_delete_source_not_found_returns_404(self, mock_del):
        mock_del.return_value = 0
        res = client.delete("/rag/sources?source=missing.pdf")
        assert res.status_code == 404
