import json
from typing import Any, Dict, List, Optional

from groq import Groq, BadRequestError

from app.config import settings
from app.agents.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from app.agents.memory import get_history, append_turn
from app.tracing import trace_span

SUPERVISOR_PROMPT = (
    "You are a Supervisor Agent orchestrating a team of specialists to answer user requests. "
    "You can delegate tasks to specialists or answer directly if no delegation is needed. "
    "\n\n"
    "Available Specialists:\n"
    "- 'researcher': Has access to knowledge base search (rag_lookup), web search (search_internet), and product crawling. Use for gathering information.\n"
    "- 'coder': Has access to Python execution (run_python) and a calculator. Use for data analysis, math, and coding tasks.\n"
    "\n"
    "To delegate, use the `delegate_to_specialist` tool. You can delegate multiple times. "
    "Once you have all the necessary information from the specialists, synthesize a final, comprehensive answer for the user."
    "\n\n"
    "Formatting Rules:\n"
    "1. **Referral Links**: Format product links as `[Product](url?tag=workspaceai-20)` or similar.\n"
    "2. **Mermaid Flowcharts**: Wrap node labels with spaces/symbols in double quotes.\n"
    "3. **Tool Call Format**: Use exactly `<function=tool_name>{\"param\": \"value\"}</function>`.\n"
)

RESEARCHER_PROMPT = (
    "You are a Researcher Agent. Your goal is to gather information to fulfill the instructions given to you. "
    "Use your tools (rag_lookup, search_internet, deep_research_product) to find the best information. "
    "Once you have gathered the data, synthesize it clearly and provide a comprehensive report back to the supervisor."
    "Do not use `<function=tool_name>` in your final output text, only use standard json tool calls."
)

CODER_PROMPT = (
    "You are a Coder Agent. Your goal is to execute calculations or python code to fulfill the instructions. "
    "Use your tools (run_python, calculator). Ensure you handle errors gracefully. "
    "Provide a final answer summarizing the results of your computations back to the supervisor."
    "Do not use `<function=tool_name>` in your final output text, only use standard json tool calls."
)

MAX_ITERATIONS = 15

def _run_worker(instructions: str, persona_prompt: str, tools_subset: List[Dict[str, Any]], model: str) -> str:
    """Runs a single worker agent (e.g. Researcher or Coder) until it gives a final answer."""
    client = Groq(api_key=settings.groq_api_key)
    messages = [
        {"role": "system", "content": persona_prompt},
        {"role": "user", "content": instructions}
    ]
    
    for _ in range(8):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_subset,
                tool_choice="auto",
            )
        except BadRequestError as e:
            return f"Worker failed: {e}"
            
        msg = response.choices[0].message
        
        assistant_turn = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_turn["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_turn)
        
        if response.choices[0].finish_reason == "stop" or not msg.tool_calls:
            return msg.content or "Task completed without detailed output."
            
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
            except Exception:
                fn_args = {}
                
            tool_fn = TOOL_REGISTRY.get(fn_name)
            tool_res = tool_fn(**fn_args) if tool_fn else {"error": "Unknown tool"}
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_res),
            })
            
    return "Worker reached maximum iterations."

def delegate_to_specialist(specialist: str, instructions: str, model: str) -> str:
    """Tool implementation for the Supervisor to delegate."""
    with trace_span("agent.delegate", {"specialist": specialist, "instructions": instructions}):
        if specialist == "researcher":
            tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in ["rag_lookup", "search_internet", "deep_research_product"]]
            return _run_worker(instructions, RESEARCHER_PROMPT, tools, model)
        elif specialist == "coder":
            tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in ["run_python", "calculator"]]
            return _run_worker(instructions, CODER_PROMPT, tools, model)
        else:
            return f"Error: Unknown specialist '{specialist}'. Use 'researcher' or 'coder'."

DELEGATE_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "delegate_to_specialist",
        "description": "Delegate a sub-task to a specialist. They will return a comprehensive report.",
        "parameters": {
            "type": "object",
            "properties": {
                "specialist": {"type": "string", "enum": ["researcher", "coder"], "description": "The specialist to use."},
                "instructions": {"type": "string", "description": "Clear, detailed instructions on what they need to do."}
            },
            "required": ["specialist", "instructions"],
        },
    },
}

def run_agent(
    user_message: str,
    model: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """The main Supervisor loop that replaces the old single-agent."""
    with trace_span("agent.run_multi_agent", {
        "user_message": user_message,
        "model": model or settings.default_model,
        "session_id": session_id
    }) as agent_span:
        client = Groq(api_key=settings.groq_api_key)
        resolved_model = model or settings.default_model

        messages: List[Dict[str, Any]] = [{"role": "system", "content": SUPERVISOR_PROMPT}]

        if session_id:
            messages.extend(get_history(session_id))

        messages.append({"role": "user", "content": user_message})

        iterations = 0
        tool_calls_made = []
        
        # Supervisor has delegate tool, plus calculator just in case it wants to do simple math directly
        # but we encourage delegation
        calculator_def = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "calculator")
        supervisor_tools = [DELEGATE_TOOL_DEF, calculator_def]

        while iterations < max_iterations:
            iterations += 1

            with trace_span(f"agent.super_iteration_{iterations}", {"model": resolved_model}):
                try:
                    with trace_span("agent.llm_completion", {"model": resolved_model}):
                        response = client.chat.completions.create(
                            model=resolved_model,
                            messages=messages,
                            tools=supervisor_tools,
                            tool_choice="auto",
                        )
                except BadRequestError as e:
                    return {
                        "answer": f"Supervisor generation failed: {e}",
                        "tool_calls_made": tool_calls_made,
                        "iterations": iterations,
                        "model": resolved_model,
                        "session_id": session_id,
                    }

                msg = response.choices[0].message
                finish_reason = response.choices[0].finish_reason

                assistant_turn: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
                if msg.tool_calls:
                    assistant_turn["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(assistant_turn)

                if finish_reason == "stop" or not msg.tool_calls:
                    answer = msg.content or ""
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

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    except Exception:
                        fn_args = {}

                    with trace_span("agent.tool_execution", {"tool_name": fn_name}):
                        if fn_name == "delegate_to_specialist":
                            specialist = fn_args.get("specialist", "")
                            instructions = fn_args.get("instructions", "")
                            res = delegate_to_specialist(specialist, instructions, resolved_model)
                            tool_result = {"result": res}
                        elif fn_name == "calculator":
                            tool_fn = TOOL_REGISTRY.get("calculator")
                            tool_result = tool_fn(**fn_args) if tool_fn else {"error": "Calculator not found"}
                        else:
                            tool_result = {"error": f"Unknown tool: {fn_name}"}

                    tool_calls_made.append({"tool": fn_name, "args": fn_args, "result": tool_result})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result),
                    })

        return {
            "answer": "Supervisor reached maximum iterations without a final answer.",
            "tool_calls_made": tool_calls_made,
            "iterations": iterations,
            "model": resolved_model,
            "session_id": session_id,
        }
