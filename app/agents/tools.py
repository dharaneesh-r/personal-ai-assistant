import math
import subprocess
import sys
from typing import Any, Dict

from app.rag.retriever import retrieve
from app.ingestion.loader import load_url
from app.ingestion.processor import process_document
from app.rag.vectorstore import add_chunks

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
    {
        "type": "function",
        "function": {
            "name": "deep_research_product",
            "description": (
                "Search the web for product brands, websites, e-commerce stores, or reviews, "
                "then scrape and ingest their contents directly into the local vector store "
                "so it can be retrieved via rag_lookup. Use this for product recommendations, brand comparison, "
                "or finding the best keyboard or other hardware."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query to research (e.g. 'zebronics keyboard models', 'best apple keyboard reviews')"},
                },
                "required": ["query"],
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


def deep_research_product(query: str, max_pages: int = 3) -> Dict[str, Any]:
    """
    Search the internet for product websites or pages, scrape their content concurrently, 
    and ingest them directly into the vector database knowledge base.
    """
    import concurrent.futures
    
    # 1. Search the web for relevant URLs
    search_res = web_search(query, max_results=max_pages * 2)
    if "error" in search_res:
        return {"error": f"Search failed: {search_res['error']}"}
        
    results = search_res.get("results", [])
    if not results:
        return {"result": "No product pages or websites found."}
        
    crawled_sources = []
    total_chunks = 0
    
    # 2. Scrape top URLs concurrently
    urls_to_scrape = [r["url"] for r in results][:max_pages]
    
    def fetch_page(url: str):
        try:
            text = load_url(url)
            return url, text
        except Exception:
            return url, None

    scraped_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_pages) as executor:
        futures = {executor.submit(fetch_page, url): url for url in urls_to_scrape}
        done, not_done = concurrent.futures.wait(futures.keys(), timeout=8.0)
        
        for fut in done:
            try:
                url, text = fut.result()
                if text and len(text.strip()) >= 100:
                    scraped_data[url] = text
            except Exception:
                pass
                
        for fut in not_done:
            fut.cancel()

    # 3. Chunk, process and index scraped data
    for url, text in scraped_data.items():
        try:
            chunks = process_document(text, source=url, source_type="url")
            stored = add_chunks(chunks)
            if stored > 0:
                crawled_sources.append(url)
                total_chunks += stored
        except Exception:
            continue
            
    return {
        "result": f"Successfully crawled and indexed {len(crawled_sources)} pages for '{query}'. Added {total_chunks} chunks to the database.",
        "crawled_urls": crawled_sources,
        "chunks_indexed": total_chunks
    }


TOOL_REGISTRY = {
    "rag_lookup": rag_lookup,
    "calculator": calculator,
    "search_internet": web_search,
    "run_python": run_python,
    "deep_research_product": deep_research_product,
}
