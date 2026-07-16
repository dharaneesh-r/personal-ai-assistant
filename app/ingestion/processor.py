import concurrent.futures
from typing import Any, Dict, List
from groq import Groq, RateLimitError
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

from app.config import settings
from app.ingestion.chunker import chunk_text


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=2, max=15),
    reraise=True
)
def _create_context_completion(client: Groq, prompt: str) -> str:
    completion = client.chat.completions.create(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.1,
    )
    return completion.choices[0].message.content.strip()


def get_context_for_chunk(client: Groq, doc_text: str, chunk_text: str) -> str:
    prompt = f"""<document>
{doc_text}
</document>

Here is the chunk we want to situate within the whole document:
<chunk>
{chunk_text}
</chunk>

Please give a short explanation (1-2 sentences) to situate this chunk in the overall document. Describe its context or importance in relation to the main themes of the document. Keep it brief and factual. Do not include any introductory remarks."""
    try:
        return _create_context_completion(client, prompt)
    except Exception:
        return ""


def process_document(
    text: str,
    source: str,
    source_type: str,
    chunk_size: int = 1500,
    overlap: int = 200,
    use_contextual: bool = False,
) -> List[Dict[str, Any]]:
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    total = len(chunks)

    contexts = [""] * total
    if use_contextual and text.strip() and settings.groq_api_key:
        client = Groq(api_key=settings.groq_api_key)
        # Cap document context text to 40k characters to avoid token limit issues in LLM calls
        doc_context = text[:40000]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(get_context_for_chunk, client, doc_context, chunk): i
                for i, chunk in enumerate(chunks)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    contexts[idx] = future.result()
                except Exception:
                    contexts[idx] = ""

    processed_chunks = []
    for i, chunk in enumerate(chunks):
        situating_context = contexts[i]
        final_text = chunk
        if situating_context:
            final_text = f"<document_context>\n{situating_context}\n</document_context>\n{chunk}"
        
        processed_chunks.append({
            "text": final_text,
            "original_text": chunk,
            "context": situating_context,
            "source": source,
            "source_type": source_type,
            "chunk_index": i,
            "total_chunks": total,
        })
    return processed_chunks
