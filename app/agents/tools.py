import math
import subprocess
import sys
from typing import Any, Dict

from app.rag.retriever import retrieve

# --- Tool definitions ---

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "rag_lookup",
            "description": (
                "Search the local knowledge base for information relevant to a query. "
                "Use this when the question may be answered by ingested documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "top_k": {"type": "integer", "description": "Number of results to return. Use 4 or more for broad questions. Default is 4."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a safe mathematical expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "A Python math expression, e.g. '2 ** 10' or 'math.sqrt(144)'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_internet",
            "description": "Search the internet for current information not available in the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a Python code snippet and return stdout. Use for data analysis, calculations, or string processing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute. Use print() to output results."},
                },
                "required": ["code"],
            },
        },
    },
]

# --- Tool implementations ---

def rag_lookup(query: str, top_k: int = 4) -> Dict[str, Any]:
    chunks = retrieve(query, top_k=top_k, score_threshold=0.2)
    if not chunks:
        return {"result": "No relevant information found in the knowledge base."}
    return {"result": [{"text": c["text"], "source": c["source"], "score": c["score"]} for c in chunks]}


def calculator(expression: str) -> Dict[str, Any]:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed["abs"] = abs
    allowed["round"] = round
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)  # noqa: S307
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def web_search(query: str, max_results: int = 3) -> Dict[str, Any]:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                snippet = r["body"][:150] if r.get("body") else ""
                results.append({"title": r["title"], "url": r["href"], "snippet": snippet})
        return {"results": results} if results else {"results": [], "note": "No results found."}
    except Exception as e:
        return {"error": str(e)}


def run_python(code: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() or None,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Code execution timed out (10s limit)"}
    except Exception as e:
        return {"error": str(e)}


TOOL_REGISTRY = {
    "rag_lookup": rag_lookup,
    "calculator": calculator,
    "search_internet": web_search,
    "run_python": run_python,
}
