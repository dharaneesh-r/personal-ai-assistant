import pytest
from unittest.mock import MagicMock, patch
from app.agents.agent import run_agent, delegate_to_specialist

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


class TestMultiAgent:
    @patch("app.agents.agent.Groq")
    def test_supervisor_answers_directly(self, mock_groq_cls):
        """Test that the supervisor answers directly without delegation when appropriate."""
        mock_groq_cls.return_value.chat.completions.create.return_value = (
            _make_groq_response("I can answer that directly: 42.")
        )
        
        result = run_agent("What is the meaning of life?")
        
        assert result["answer"] == "I can answer that directly: 42."
        assert len(result["tool_calls_made"]) == 0
        assert result["iterations"] == 1

    @patch("app.agents.agent.Groq")
    def test_supervisor_delegates_to_researcher(self, mock_groq_cls):
        """Test that the supervisor delegates to the researcher."""
        tool_call = MagicMock()
        tool_call.id = "call_delegate_researcher"
        tool_call.function.name = "delegate_to_specialist"
        tool_call.function.arguments = '{"specialist": "researcher", "instructions": "Find the capital of France"}'
        
        create = mock_groq_cls.return_value.chat.completions.create
        # 1. Supervisor delegates
        # 2. Researcher agent answers
        # 3. Supervisor synthesizes
        create.side_effect = [
            _make_groq_response("", tool_calls=[tool_call], finish_reason="tool_calls"), # Supervisor
            _make_groq_response("The capital of France is Paris.", finish_reason="stop"), # Researcher worker
            _make_groq_response("The researcher found that the capital of France is Paris.", finish_reason="stop"), # Supervisor final
        ]
        
        result = run_agent("Find the capital of France.")
        
        assert "Paris" in result["answer"]
        assert len(result["tool_calls_made"]) == 1
        assert result["tool_calls_made"][0]["tool"] == "delegate_to_specialist"
        assert result["tool_calls_made"][0]["args"]["specialist"] == "researcher"

    @patch("app.agents.agent.Groq")
    def test_supervisor_delegates_to_coder(self, mock_groq_cls):
        """Test that the supervisor delegates to the coder."""
        tool_call = MagicMock()
        tool_call.id = "call_delegate_coder"
        tool_call.function.name = "delegate_to_specialist"
        tool_call.function.arguments = '{"specialist": "coder", "instructions": "Calculate 10 * 10"}'
        
        create = mock_groq_cls.return_value.chat.completions.create
        create.side_effect = [
            _make_groq_response("", tool_calls=[tool_call], finish_reason="tool_calls"), # Supervisor
            _make_groq_response("100", finish_reason="stop"), # Coder worker
            _make_groq_response("The answer is 100.", finish_reason="stop"), # Supervisor final
        ]
        
        result = run_agent("Calculate 10 * 10")
        
        assert "100" in result["answer"]
        assert len(result["tool_calls_made"]) == 1
        assert result["tool_calls_made"][0]["tool"] == "delegate_to_specialist"
        assert result["tool_calls_made"][0]["args"]["specialist"] == "coder"
