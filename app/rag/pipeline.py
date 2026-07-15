import json
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from app.config import settings
from app.rag.retriever import retrieve
from app.rag.graphstore import get_neighborhood

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY the context "
    "provided below. If the context does not contain enough information, say so honestly. "
    "Be extremely forgiving of typos, spelling mistakes, and grammatical issues. "
    "Intelligently deduce user intent and answer directly instead of asking for clarifications. "
    "If the user asks for a chart or table, output the requested chart (in Mermaid format) or table "
    "based on the context of the conversation. "
    "IMPORTANT: When generating Mermaid charts, you MUST obey these syntax rules:\n"
    "1. Node IDs (variable names) must be strictly single alphanumeric words without spaces, dots, or special characters. Use snake_case (e.g. dharaneesh_r or node_js).\n"
    "2. Always enclose node labels in double quotes (e.g., dharaneesh_r[\"Dharaneesh R\"] or node_js[\"Node.js\"]).\n"
    "3. Links with text must be formatted as: A -->|text| B (do NOT write A -->|text|> B).\n"
    "Example of correct code:\n"
    "graph TB\n"
    "    dharaneesh[\"Dharaneesh R\"] -->|Skills| node_js[\"Node.js\"]"
)

_CONTEXT_TEMPLATE = """Context:
{context}

Question: {question}"""

_REWRITE_PROMPT = (
    "Rewrite the following question to be more specific and search-friendly for a document retrieval system. "
    "Return ONLY the rewritten question, nothing else.\n\nOriginal: {question}"
)


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] (source: {chunk['source']})\n{chunk['text']}")
    return "\n\n".join(parts)


_EXTRACT_ENTITIES_PROMPT = """Identify the main names, technologies, key concepts, or noun entities in the following question.
Respond with a JSON object containing a key "entities" mapping to a list of extracted strings.
Do not include any other text.

Question: {question}

Example Output:
{{
  "entities": ["FastAPI", "Python", "John Doe"]
}}"""


def _extract_entities_from_query(question: str, client: Groq, model: str) -> List[str]:
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _EXTRACT_ENTITIES_PROMPT.format(question=question)}],
            response_format={"type": "json_object"},
            max_tokens=100,
            temperature=0.0
        )
        raw = completion.choices[0].message.content.strip()
        data = json.loads(raw)
        return data.get("entities", [])
    except Exception:
        import re
        words = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', question)
        return list(set(words))


def _rewrite_query(question: str, client: Groq, model: str) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _REWRITE_PROMPT.format(question=question)}],
        max_tokens=100,
    )
    return completion.choices[0].message.content.strip()


def rag_query(
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.1,
    model: Optional[str] = None,
    source_filter: Optional[List[str]] = None,
    use_hybrid: bool = False,
    use_rerank: bool = False,
    rewrite_query: bool = False,
    use_graph: bool = False,
    history: Optional[List[Tuple[str, str]]] = None,
) -> Dict[str, Any]:
    resolved_model = model or settings.default_model
    client = Groq(api_key=settings.groq_api_key)

    search_query = question
    rewritten = None
    if rewrite_query:
        rewritten = _rewrite_query(question, client, resolved_model)
        search_query = rewritten

    chunks = retrieve(
        search_query,
        top_k=top_k,
        score_threshold=score_threshold,
        source_filter=source_filter,
        use_hybrid=use_hybrid,
        use_rerank=use_rerank,
    )

    graph_facts = []
    graph_sources = []
    if use_graph:
        entities = _extract_entities_from_query(question, client, resolved_model)
        if entities:
            res = get_neighborhood(entities)
            graph_facts = res.get("facts", [])
            graph_sources = res.get("sources", [])

    if not chunks and not graph_facts:
        return {
            "answer": "I could not find any relevant information in the knowledge base.",
            "sources": [],
            "chunks_used": 0,
            "model": resolved_model,
            "rewritten_query": rewritten,
        }

    # Format the context
    context_parts = []
    if use_graph and graph_facts:
        context_parts.append("Graph Knowledge Base Facts:\n" + "\n".join(graph_facts))
    
    if chunks:
        context_parts.append("Retrieved Text Passages:\n" + _build_context(chunks))
        
    context = "\n\n".join(context_parts)
    prompt = _CONTEXT_TEMPLATE.format(context=context, question=question)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if history:
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(model=resolved_model, messages=messages)

    # Combine sources from both vector store and knowledge graph
    all_sources = list(set([c["source"] for c in chunks] + graph_sources))

    return {
        "answer": completion.choices[0].message.content,
        "sources": all_sources,
        "chunks_used": len(chunks),
        "model": resolved_model,
        "rewritten_query": rewritten,
    }
