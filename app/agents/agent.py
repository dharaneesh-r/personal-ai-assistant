import json
from typing import Any, Dict, List, Optional

from groq import Groq, BadRequestError

from app.config import settings
from app.agents.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from app.agents.memory import get_history, append_turn
from app.tracing import trace_span

_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to tools. "
    "Use rag_lookup to search the knowledge base. "
    "Use deep_research_product to crawl and index websites before answering product recommendations, comparisons, or finding the 'best' models. "
    "Use search_internet for general current events not in the knowledge base. "
    "Use run_python for code execution, and calculator for simple math. "
    "\n"
    "When suggesting products:\n"
    "1. **Budget Check**: If the user mentions a budget (or asks for cheap/premium products), identify it and suggest 2-3 alternative models within that budget.\n"
    "2. **Referral/Affiliate Links**: Format all product links as markdown links with referral tags:\n"
    "   - Amazon search: `https://www.amazon.com/s?k=[product_name_encoded]&tag=workspaceai-20` (e.g., `[Keychron K2](https://www.amazon.com/s?k=Keychron+K2&tag=workspaceai-20)`)\n"
    "   - Flipkart search: `https://www.flipkart.com/search?q=[product_name_encoded]&affid=workspaceai`\n"
    "   - Brand websites: Append `?ref=workspaceai` to the original page URL.\n"
    "3. **Mermaid Flowcharts**: Always wrap node labels containing spaces, parentheses, hyphens, or special symbols in double quotes (e.g., A[\"Query (Text)\"] instead of A[Query (Text)]). Node IDs (variable names) must be strictly single alphanumeric words (letters, numbers, underscores). NO slashes (/), spaces, hyphens, dots, or other special characters. (e.g. use rtgs_neft, NOT RTGS/NEFT).\n"
    "4. **Tool Call Format**: If you call a function, you must write it strictly in this format: `<function=tool_name>{\"param\": \"value\"}</function>`. Ensure the closing angle bracket `>` is always present right after the tool name. Do not write `<function=tool_name=arguments`.\n"
    "\n"
    "Think step by step and give detailed, structured answers."
)

MAX_ITERATIONS = 10


def run_agent(
    user_message: str,
    model: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    with trace_span("agent.run_agent", {
        "user_message": user_message,
        "model": model or settings.default_model,
        "session_id": session_id
    }) as agent_span:
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

            with trace_span(f"agent.iteration_{iterations}", {"model": resolved_model}) as iter_span:
                try:
                    with trace_span("agent.llm_completion", {"model": resolved_model}) as llm_span:
                        response = client.chat.completions.create(
                            model=resolved_model,
                            messages=messages,
                            tools=TOOL_DEFINITIONS,
                            tool_choice="auto",
                        )
                except BadRequestError as e:
                    iter_span.set_attribute("error", str(e))
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
                    agent_span.set_attribute("final_answer", answer[:200] + "...")
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
                        if isinstance(tc.function.arguments, dict):
                            fn_args = tc.function.arguments
                        elif isinstance(tc.function.arguments, str) and tc.function.arguments.strip():
                            fn_args = json.loads(tc.function.arguments)
                        else:
                            fn_args = {}
                    except Exception:
                        fn_args = {}

                    with trace_span("agent.tool_execution", {"tool_name": fn_name, "args": str(fn_args)}) as tool_span:
                        tool_fn = TOOL_REGISTRY.get(fn_name)
                        tool_result = tool_fn(**fn_args) if tool_fn else {"error": f"Unknown tool: {fn_name}"}
                        tool_span.set_attribute("tool_result", str(tool_result)[:500])

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
