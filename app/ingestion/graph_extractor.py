import json
from typing import Any, Dict, List, Optional
from groq import Groq, RateLimitError
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

from app.config import settings

_EXTRACTION_SYSTEM_PROMPT = """You are an expert knowledge graph extraction engine.
Analyze the provided text and extract a list of entities (nodes) and relations (edges) connecting them.

For each entity, extract:
- name: The canonical name of the entity (e.g. "Google", "FastAPI", "John Doe"). Keep it short and clean.
- type: The category, which must be one of: [person, organization, technology, concept, event, location, other]
- description: A brief one-sentence description of what this entity is in the context of the text.

For each relation, extract:
- source: The name of the source entity (must match the name of an entity in the entities list).
- target: The name of the target entity (must match the name of an entity in the entities list).
- type: The relationship type. Keep it short (e.g. "works_at", "uses", "created", "part_of", "version_of", "collaborates_with", "subconcept_of").
- description: A brief one-sentence description explaining why this relationship exists.

Your output must be a valid JSON object with the keys "entities" and "relations".
Do not include any introductory or concluding text.

Example JSON output format:
{
  "entities": [
    {"name": "Dharaneesh", "type": "person", "description": "A software engineer working on AI applications."},
    {"name": "FastAPI", "type": "technology", "description": "An async web framework for building APIs with Python."}
  ],
  "relations": [
    {"source": "Dharaneesh", "target": "FastAPI", "type": "uses", "description": "Dharaneesh uses FastAPI to build backends."}
  ]
}"""


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=2, max=15),
    reraise=True
)
def _completions_create_with_retry(client: Groq, **kwargs):
    return client.chat.completions.create(**kwargs)


def extract_graph_from_text(
    text: str,
    model: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Uses Groq to extract entities and relations from a text block in JSON format."""
    if not text or not text.strip():
        return {"entities": [], "relations": []}

    client = Groq(api_key=settings.groq_api_key)
    resolved_model = model or settings.default_model

    # Limit text length to avoid token limit issues in local embedding/extraction
    truncated_text = text[:8000]

    try:
        response = _completions_create_with_retry(
            client,
            model=resolved_model,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract entities and relations from the following text:\n\n{truncated_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )

        raw_content = response.choices[0].message.content
        if not raw_content:
            return {"entities": [], "relations": []}

        data = json.loads(raw_content)
        
        # Ensure correct structure
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        
        # Simple cleanup and validation
        cleaned_entities = []
        entity_names = set()
        for ent in entities:
            name = ent.get("name", "").strip()
            ent_type = ent.get("type", "other").strip().lower()
            desc = ent.get("description", "").strip()
            
            if name and name not in entity_names:
                entity_names.add(name)
                cleaned_entities.append({
                    "name": name,
                    "type": ent_type if ent_type in ["person", "organization", "technology", "concept", "event", "location", "other"] else "other",
                    "description": desc
                })

        cleaned_relations = []
        for rel in relations:
            src = rel.get("source", "").strip()
            tgt = rel.get("target", "").strip()
            rel_type = rel.get("type", "").strip().lower()
            desc = rel.get("description", "").strip()
            
            # Only keep relations if both entities are extracted/present
            if src and tgt and rel_type:
                cleaned_relations.append({
                    "source": src,
                    "target": tgt,
                    "type": rel_type,
                    "description": desc
                })
                
        return {
            "entities": cleaned_entities,
            "relations": cleaned_relations
        }

    except Exception as e:
        # Fallback to empty graph on API failure
        import logging
        logging.getLogger("uvicorn.error").error(f"Error during graph extraction: {e}")
        return {"entities": [], "relations": []}
