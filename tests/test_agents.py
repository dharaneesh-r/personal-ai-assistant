"""Tests for the tool-calling agent and agent API endpoints."""
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_groq_response(content: str, tool_calls=None, finish_reason="stop"):
    """Build a mock Groq chat completion response."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = finish_reason
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── agent core ────────────────────────────────────────────────────────────────

class TestRunAgent:
    @patch("app.agents.agent.Groq")
    def test_simple_answer_no_tools(self, mock_groq_cls):
        mock_groq_cls.return_value.chat.completions.create.return_value = (
            _make_groq_response("Paris is the capital of France.")
        )
        from app.agents.agent import run_agent
        result = run_agent("What is the capital of France?")

        assert result["answer"] == "Paris is the capital of France."
        assert result["tool_calls_made"] == []
        assert result["iterations"] == 1

    @patch("app.agents.agent.Groq")
    @patch("app.agents.agent.TOOL_REGISTRY", {"calculator": lambda expression: {"result": 42}})
    def test_tool_call_then_final_answer(self, mock_groq_cls):
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "calculator"
        tool_call.function.arguments = '{"expression": "6 * 7"}'

        create = mock_groq_cls.return_value.chat.completions.create
        create.side_effect = [
            _make_groq_response("", tool_calls=[tool_call], finish_reason="tool_calls"),
            _make_groq_response("The answer is 42."),
        ]

        from app.agents.agent import run_agent
        result = run_agent("What is 6 times 7?")

        assert result["answer"] == "The answer is 42."
        assert len(result["tool_calls_made"]) == 1
        assert result["tool_calls_made"][0]["tool"] == "calculator"
        assert result["tool_calls_made"][0]["result"] == {"result": 42}
        assert result["iterations"] == 2

    @patch("app.agents.agent.Groq")
    def test_unknown_tool_returns_error_in_result(self, mock_groq_cls):
        tool_call = MagicMock()
        tool_call.id = "call_x"
        tool_call.function.name = "nonexistent_tool"
        tool_call.function.arguments = "{}"

        create = mock_groq_cls.return_value.chat.completions.create
        create.side_effect = [
            _make_groq_response("", tool_calls=[tool_call], finish_reason="tool_calls"),
            _make_groq_response("I could not use that tool."),
        ]

        from app.agents.agent import run_agent
        result = run_agent("Use nonexistent tool")
        assert "error" in result["tool_calls_made"][0]["result"]

    @patch("app.agents.agent.Groq")
    def test_max_iterations_guard(self, mock_groq_cls):
        tool_call = MagicMock()
        tool_call.id = "call_loop"
        tool_call.function.name = "calculator"
        tool_call.function.arguments = '{"expression": "1+1"}'

        mock_groq_cls.return_value.chat.completions.create.return_value = (
            _make_groq_response("", tool_calls=[tool_call], finish_reason="tool_calls")
        )

        from app.agents.agent import run_agent
        result = run_agent("Loop forever", max_iterations=3)

        assert result["iterations"] == 3
        assert "maximum iterations" in result["answer"].lower()

    @patch("app.agents.agent.Groq")
    @patch("app.agents.agent.get_history", return_value=[])
    @patch("app.agents.agent.append_turn")
    def test_session_history_injected(self, mock_append, mock_history, mock_groq_cls):
        mock_groq_cls.return_value.chat.completions.create.return_value = (
            _make_groq_response("Answer with memory.")
        )
        from app.agents.agent import run_agent
        result = run_agent("Hello", session_id="sess-123")

        mock_history.assert_called_once_with("sess-123")
        mock_append.assert_called_once_with("sess-123", "Hello", "Answer with memory.")
        assert result["session_id"] == "sess-123"


# ── agent API endpoints ───────────────────────────────────────────────────────

class TestAgentEndpoints:
    @patch("app.api.routes_agent.run_agent")
    def test_run_endpoint_success(self, mock_run):
        mock_run.return_value = {
            "answer": "42",
            "tool_calls_made": [],
            "iterations": 1,
            "model": "llama-3.3-70b-versatile",
            "session_id": None,
        }
        res = client.post("/agent/run", json={"message": "What is 6*7?"})
        assert res.status_code == 200
        assert res.json()["answer"] == "42"

    def test_run_endpoint_missing_message_returns_422(self):
        res = client.post("/agent/run", json={})
        assert res.status_code == 422

    def test_create_session(self):
        res = client.post("/agent/session")
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data

    def test_delete_session(self):
        create_res = client.post("/agent/session")
        sid = create_res.json()["session_id"]
        del_res = client.delete(f"/agent/session/{sid}")
        assert del_res.status_code == 200

    def test_delete_nonexistent_session_returns_404(self):
        res = client.delete("/agent/session/does-not-exist")
        assert res.status_code == 404

    @patch("app.agents.tools.web_search")
    @patch("app.agents.tools.load_url")
    @patch("app.agents.tools.process_document")
    @patch("app.agents.tools.add_chunks")
    def test_deep_research_product_success(self, mock_add_chunks, mock_process_doc, mock_load_url, mock_web_search):
        mock_web_search.return_value = {
            "results": [
                {"title": "Zebronics Keyboard", "url": "https://zebronics.com/keyboard", "snippet": "zebronics is best"}
            ]
        }
        mock_load_url.return_value = "This is a Zebronics keyboard model description. It is a very good mechanical keyboard with custom switches, keycaps, and beautiful RGB lighting that works perfectly."
        mock_process_doc.return_value = [{"text": "This is a Zebronics keyboard model description. It is a very good mechanical keyboard with custom switches, keycaps, and beautiful RGB lighting that works perfectly.", "source": "https://zebronics.com/keyboard", "chunk_index": 0, "source_type": "url", "total_chunks": 1}]
        mock_add_chunks.return_value = 1
        
        from app.agents.tools import deep_research_product
        result = deep_research_product("best zebronics keyboard", max_pages=1)
        
        assert "Successfully crawled and indexed 1 pages" in result["result"]
        assert result["chunks_indexed"] == 1
        assert "https://zebronics.com/keyboard" in result["crawled_urls"]
