import json
from typing import Any, Dict, List

from groq import Groq

from app.config import settings

_FAITHFULNESS_PROMPT = """You are an evaluation judge. Score the FAITHFULNESS of an answer — whether it only uses information from the given context.

Context:
{context}

Question: {question}
Answer: {answer}

Score from 1-5:
1 = answer contradicts or ignores the context entirely
3 = answer is partially grounded in context
5 = answer is fully supported by the context, no hallucinations

Respond with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}"""

_RELEVANCE_PROMPT = """You are an evaluation judge. Score the RELEVANCE of an answer to the question.

Question: {question}
Answer: {answer}

Score from 1-5:
1 = answer is completely off-topic
3 = answer partially addresses the question
5 = answer directly and completely addresses the question

Respond with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}"""

_GROUNDEDNESS_PROMPT = """You are an evaluation judge. Score the GROUNDEDNESS — whether the answer's claims can be traced back to specific parts of the context.

Context:
{context}

Answer: {answer}

Score from 1-5:
1 = no claims are traceable to the context
3 = some claims are traceable
5 = every claim maps directly to the context

Respond with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}"""


def _judge(prompt: str, model: str) -> Dict[str, Any]:
    client = Groq(api_key=settings.groq_api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )
    raw = completion.choices[0].message.content.strip()
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"score": 0, "reason": "parse error"}


def evaluate(
    question: str,
    answer: str,
    context: str,
    model: str = "llama-3.1-8b-instant",
) -> Dict[str, Any]:
    faithfulness = _judge(_FAITHFULNESS_PROMPT.format(context=context, question=question, answer=answer), model)
    relevance = _judge(_RELEVANCE_PROMPT.format(question=question, answer=answer), model)
    groundedness = _judge(_GROUNDEDNESS_PROMPT.format(context=context, answer=answer), model)

    scores = [faithfulness["score"], relevance["score"], groundedness["score"]]
    overall = round(sum(scores) / len(scores), 2)

    return {
        "overall": overall,
        "faithfulness": faithfulness,
        "relevance": relevance,
        "groundedness": groundedness,
    }


def batch_evaluate(items: List[Dict[str, Any]], model: str = "llama-3.1-8b-instant") -> List[Dict[str, Any]]:
    results = []
    for item in items:
        result = evaluate(
            question=item["question"],
            answer=item["answer"],
            context=item["context"],
            model=model,
        )
        results.append({"question": item["question"], **result})
    return results
