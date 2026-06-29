Add a new tool to the Groq tool-calling agent.

The user will describe the tool (e.g. "web search", "calculator", "RAG lookup", "weather", "code executor").

Steps:
1. Read `app/agents/tools.py` to see existing tools.
2. Define the new tool following the Groq function-calling schema:
   - A Python function that executes the tool logic
   - A `TOOL_DEFINITION` dict with `name`, `description`, and `parameters` (JSON Schema)
3. Register the new tool in the `TOOLS` list and `TOOL_MAP` dispatch dict in `tools.py`.
4. Read `app/agents/agent.py` — the agent loop calls tools via `TOOL_MAP[name](**args)`. Verify your tool fits this pattern.
5. If the tool calls an external API, read credentials from `app/config.py` (Settings) — add the env var there and to `.env.example` if it exists.
6. Keep tool functions pure where possible — side effects only when necessary (e.g. writing files).

Tool function signature: `def tool_name(**kwargs) -> str` — always return a string the LLM can read.

Do not modify the agent loop in `agent.py` unless the new tool requires a structural change (e.g. streaming, async).
