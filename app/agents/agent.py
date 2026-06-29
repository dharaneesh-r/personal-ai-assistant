import json
from typing import Any, Dict, List, Optional

from groq import Groq, BadRequestError

from app.config import settings
from app.agents.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from app.agents.memory import get_history, append_turn

_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use rag_lookup to search the knowledge base before answering factual questions — always use top_k=4 or higher for broad questions. "
    "If the first lookup does not give enough detail, call rag_lookup again with a more specific query. "
    "Use search_internet for current events or information not in the knowledge base. "
    "Use run_python for calculations, data processing, or code execution. "
    "Use calculator for simple math expressions. "
    "Think step by step and give complete, detailed answers."
)

MAX_ITERATIONS = 10


def run_agent(
    user_message: str,
    model: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    client = Groq(api_key=settings.groq_api_key)
    resolved_model = model or settings.default_model

    messages: List[Dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    # Inject session memory
    if session_id:
        messages.extend(get_history(session_id))

    messages.append({"role": "user", "content": user_message})

    iterations = 0
    tool_calls_made = []

    while iterations < max_iterations:
        iterations += 1

        try:
            response = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        except BadRequestError as e:
            return {
                "answer": f"The model failed to generate a tool call for this query. Try rephrasing or use a different tab. (Detail: {e})",
                "tool_calls_made": tool_calls_made,
                "iterations": iterations,
                "model": resolved_model,
                "session_id": session_id,
            }

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        assistant_turn: Dict[str, Any] = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            assistant_turn["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_turn)

        if finish_reason == "stop" or not message.tool_calls:
            answer = message.content or ""
            if session_id:
                append_turn(session_id, user_message, answer)
            return {
                "answer": answer,
                "tool_calls_made": tool_calls_made,
                "iterations": iterations,
                "model": resolved_model,
                "session_id": session_id,
            }

        for tc in message.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            tool_fn = TOOL_REGISTRY.get(fn_name)
            tool_result = tool_fn(**fn_args) if tool_fn else {"error": f"Unknown tool: {fn_name}"}
            tool_calls_made.append({"tool": fn_name, "args": fn_args, "result": tool_result})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result),
            })

    return {
        "answer": "Agent reached maximum iterations without a final answer.",
        "tool_calls_made": tool_calls_made,
        "iterations": iterations,
        "model": resolved_model,
        "session_id": session_id,
    }
