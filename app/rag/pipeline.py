from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from app.config import settings
from app.rag.retriever import retrieve

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY the context "
    "provided below. If the context does not contain enough information, say so honestly."
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
    source_filter: Optional[str] = None,
    use_hybrid: bool = False,
    use_rerank: bool = False,
    rewrite_query: bool = False,
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

    if not chunks:
        return {
            "answer": "I could not find any relevant information in the knowledge base.",
            "sources": [],
            "chunks_used": 0,
            "model": resolved_model,
            "rewritten_query": rewritten,
        }

    context = _build_context(chunks)
    prompt = _CONTEXT_TEMPLATE.format(context=context, question=question)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if history:
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(model=resolved_model, messages=messages)

    return {
        "answer": completion.choices[0].message.content,
        "sources": list({c["source"] for c in chunks}),
        "chunks_used": len(chunks),
        "model": resolved_model,
        "rewritten_query": rewritten,
    }
