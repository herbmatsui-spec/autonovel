"""
routers/cost.py - 執筆コスト・トークン最適化ダッシュボード API

CostRepository に記録されたトークン使用量を集計し、
推定コスト・タスク別内訳・時系列・予算アラートを提供する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, text

from src.backend.database.models import CostLogModel
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.services.cost_analytics import check_budget_alert, estimate_cost_usd
from src.services.cost_budget_guard import BudgetStatus, CostBudgetGuard

router = APIRouter(prefix="/api/cost", tags=["cost"])


class CostRecordRequest(BaseModel):
    task_type: str = "writing"
    ep_num: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    branch_id: int = 1


class BudgetRequest(BaseModel):
    budget_usd: float


class BudgetUpdate(BaseModel):
    budget_usd: float


@router.post("/books/{book_id}/records")
async def add_cost_record(book_id: int, req: CostRecordRequest) -> dict[str, Any]:
    """執筆ごとのトークン使用量を記録する（推定コストを自動算出）。"""
    est = estimate_cost_usd(req.task_type, req.input_tokens, req.output_tokens)
    async with UnitOfWork(AppContainer.db()) as uow:
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
async def cost_summary(book_id: int, branch_id: int = 1) -> dict[str, Any]:
    """コスト集計サマリーを取得する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        agg = await uow.cost.aggregate(book_id, branch_id)
    return agg


@router.post("/books/{book_id}/budget")
async def set_budget(book_id: int, req: BudgetRequest) -> dict[str, Any]:
    """予算を設定する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.cost.set_budget(book_id, req.budget_usd)
    return {"status": "success", "budget_usd": req.budget_usd}


@router.get("/books/{book_id}/budget-status")
async def budget_status(
    book_id: int, branch_id: int = 1, budget_usd: float | None = None
) -> dict[str, Any]:
    """予算ステータス（超過判定）を取得する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        agg = await uow.cost.aggregate(book_id, branch_id)
    return check_budget_alert(agg["total_cost_usd"], budget_usd)


@router.get("/budget/{book_id}")
async def get_budget(book_id: int, branch_id: int = 1) -> dict[str, Any]:
    """現在の消費金額・上限予算・ダウングレード状態を返却する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        result = await uow.session.execute(
            select(CostLogModel).where(CostLogModel.book_id == book_id)
        )
        logs = list(result.scalars().all())
        current_cost = sum(log.cost_usd for log in logs)

        budget_row = await uow.session.execute(
            text("SELECT value FROM internal_state WHERE key = :k").bindparams(k=f"budget_usd:{book_id}")
        )
        budget_value = budget_row.scalar_one_or_none()

    budget_usd = float(budget_value) if budget_value is not None else 5.0

    guard = CostBudgetGuard()
    guard.set_book_budget(book_id, budget_usd)
    guard._cost_provider = lambda bid: current_cost if bid == book_id else 0.0

    status = guard.check_budget_status(book_id)
    recommended = guard.get_recommended_model_for_task("writing", book_id)

    return {
        "book_id": book_id,
        "budget_usd": budget_usd,
        "current_cost_usd": round(current_cost, 4),
        "ratio": round(current_cost / budget_usd, 4) if budget_usd > 0 else 0.0,
        "status": status.value,
        "downgrade_active": status in (BudgetStatus.WARNING, BudgetStatus.EXCEEDED),
        "recommended_model": recommended,
    }


@router.post("/budget/{book_id}")
async def set_budget_endpoint(book_id: int, req: BudgetUpdate) -> dict[str, Any]:
    """ユーザーが作品ごとの上限金額を変更・設定できるエンドポイント。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        uow.session.execute(
            text(
                "INSERT INTO internal_state(key, value) VALUES (:k, :v) "
                "ON CONFLICT(key) DO UPDATE SET value=:v"
            ).bindparams(k=f"budget_usd:{book_id}", v=str(req.budget_usd))
        )
    return {"status": "success", "book_id": book_id, "budget_usd": req.budget_usd}
