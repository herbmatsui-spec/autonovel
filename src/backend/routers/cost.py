"""
routers/cost.py - 執筆コスト・トークン最適化ダッシュボード API

CostRepository に記録されたトークン使用量を集計し、
推定コスト・タスク別内訳・時系列・予算アラートを提供する。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.services.cost_analytics import check_budget_alert, estimate_cost_usd

router = APIRouter(prefix="/api/cost", tags=["cost"])


class CostRecordRequest(BaseModel):
    task_type: str = "writing"
    ep_num: Optional[int] = None
    input_tokens: int = 0
    output_tokens: int = 0
    branch_id: int = 1


class BudgetRequest(BaseModel):
    budget_usd: float


@router.post("/books/{book_id}/records")
async def add_cost_record(book_id: int, req: CostRecordRequest) -> Dict[str, Any]:
    """執筆ごとのトークン使用量を記録する（推定コストを自動算出）。"""
    est = estimate_cost_usd(req.task_type, req.input_tokens, req.output_tokens)
    async with UnitOfWork(Container.db()) as uow:
        rec_id = await uow.cost.add(
            book_id=book_id,
            branch_id=req.branch_id,
            task_type=req.task_type,
            input_tokens=req.input_tokens,
            output_tokens=req.output_tokens,
            total_tokens=req.input_tokens + req.output_tokens,
            est_cost_usd=est,
            ep_num=req.ep_num,
        )
    return {"status": "success", "id": rec_id, "est_cost_usd": est}


@router.get("/books/{book_id}/summary")
async def cost_summary(book_id: int, branch_id: int = 1) -> Dict[str, Any]:
    """コスト集計サマリーを取得する。"""
    async with UnitOfWork(Container.db()) as uow:
        agg = await uow.cost.aggregate(book_id, branch_id)
    return agg


@router.post("/books/{book_id}/budget")
async def set_budget(book_id: int, req: BudgetRequest) -> Dict[str, Any]:
    """予算を設定する。"""
    async with UnitOfWork(Container.db()) as uow:
        await uow.cost.set_budget(book_id, req.budget_usd)
    return {"status": "success", "budget_usd": req.budget_usd}


@router.get("/books/{book_id}/budget-status")
async def budget_status(book_id: int, branch_id: int = 1, budget_usd: Optional[float] = None) -> Dict[str, Any]:
    """予算ステータス（超過判定）を取得する。"""
    async with UnitOfWork(Container.db()) as uow:
        agg = await uow.cost.aggregate(book_id, branch_id)
    return check_budget_alert(agg["total_cost_usd"], budget_usd)
