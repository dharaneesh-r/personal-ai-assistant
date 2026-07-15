from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

from app.eval.evaluator import evaluate, batch_evaluate
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRequest(BaseModel):
    question: str
    answer: str
    context: str
    model: str = "llama-3.1-8b-instant"


class EvalScore(BaseModel):
    score: int
    reason: str


class EvalResponse(BaseModel):
    overall: float
    faithfulness: EvalScore
    relevance: EvalScore
    groundedness: EvalScore


class BatchEvalItem(BaseModel):
    question: str
    answer: str
    context: str


class BatchEvalRequest(BaseModel):
    items: List[BatchEvalItem]
    model: str = "llama-3.1-8b-instant"


@router.post("/run", response_model=EvalResponse)
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def run_eval(request: Request, eval_request: EvalRequest):
    try:
        result = evaluate(
            question=eval_request.question,
            answer=eval_request.answer,
            context=eval_request.context,
            model=eval_request.model,
        )
        return EvalResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
@limiter.limit(f"{settings.rate_limit_default}/minute")
async def run_batch_eval(request: Request, batch_request: BatchEvalRequest):
    try:
        items = [i.model_dump() for i in batch_request.items]
        return batch_evaluate(items, model=batch_request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
