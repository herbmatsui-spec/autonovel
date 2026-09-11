from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .cost_budget_guard import CostBudgetGuard
from .cost_metrics import CostMetrics

router = APIRouter()


class BudgetRequest(BaseModel):
    limit: float
    threshold_percentage: float = 90.0


class BudgetResponse(BaseModel):
    limit: float
    current_usage: float
    threshold_percentage: float
    status: str


@router.get("/admin/cost/budget", response_model=BudgetResponse)
async def get_budget_status() -> BudgetResponse:
    """
    現在の予算状況を返す管理API。
    """
    return BudgetResponse(
        limit=10.0,
        current_usage=0.0,
        threshold_percentage=90.0,
        status="normal",
    )


@router.post("/admin/cost/budget", response_model=BudgetResponse)
async def update_budget(request: BudgetRequest) -> BudgetResponse:
    """
    予算上限を更新する管理API。
    """
    return BudgetResponse(
        limit=request.limit,
        current_usage=0.0,
        threshold_percentage=request.threshold_percentage,
        status="normal",
    )
