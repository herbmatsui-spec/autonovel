from dataclasses import dataclass
from enum import Enum
from src.services.cost_analytics import CostCalculator
from src.backend.database.repositories import CostRepository
from sqlalchemy.ext.asyncio import AsyncSession


class BudgetStatus(Enum):
    NORMAL = "normal"      # 70%未満
    WARNING = "warning"    # 70-90%
    EXCEEDED = "exceeded"  # 100%超


@dataclass
class CostBudgetGuard:
    """予算監視と自動モデルダウングレードを行うガードクラス"""

    def __init__(self, calculator: CostCalculator, budget_limit: float):
        self.calculator = calculator
        self.budget_limit = budget_limit

    async def check_budget_status_async(self, db_session: AsyncSession, book_id: int) -> BudgetStatus:
        """実際の消費金額をDBから集計して予算状況を返す。"""
        # 実際の消費金額をDBから集計
        repo = CostRepository(db_session)
        aggregate_result = await repo.aggregate(book_id)
        total_cost = aggregate_result["total_cost_usd"]
        
        if self.budget_limit <= 0:
            return BudgetStatus.NORMAL

        ratio = total_cost / self.budget_limit

        if ratio < 0.7:
            return BudgetStatus.NORMAL
        elif ratio < 0.9:
            return BudgetStatus.WARNING
        return BudgetStatus.EXCEEDED

    async def get_recommended_model_for_task_async(self, db_session: AsyncSession, task_type: str, book_id: int) -> str:
        """予算警告（90%超）または超過（100%超）時に、大型モデルから高速廉価モデルへ自動切替"""
        # 実際の消費金額をDBから集計
        repo = CostRepository(db_session)
        aggregate_result = await repo.aggregate(book_id)
        total_cost_usd = aggregate_result["total_cost_usd"]

        if self.budget_limit <= 0:
            ratio = 0.0
        else:
            ratio = total_cost_usd / self.budget_limit

        # 予算上限の90%超えでダウングレード
        if ratio >= 0.9:
            # 簡易的に高速で安価なモデルを返す
            return "openai/gpt-4o-mini"
        return "openai/gpt-4o"