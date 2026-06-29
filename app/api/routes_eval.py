from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.eval.evaluator import evaluate, batch_evaluate

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
async def run_eval(request: EvalRequest):
    try:
        result = evaluate(
            question=request.question,
            answer=request.answer,
            context=request.context,
            model=request.model,
        )
        return EvalResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def run_batch_eval(request: BatchEvalRequest):
    try:
        items = [i.model_dump() for i in request.items]
        return batch_evaluate(items, model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
