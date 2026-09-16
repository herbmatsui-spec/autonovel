"""リアルタイムトークンバジェットトラッカー。"""
from __future__ import annotations
from src.services.billing.cost_budget_guard import CostBudgetConfig


class CostBudgetExceededError(Exception):
    """設定されたトークンまたは原価予算の上限を超過した場合の例外。"""
    pass


class TokenBudgetTracker:
    def __init__(self, config: CostBudgetConfig | None = None):
        self.config = config or CostBudgetConfig()
        self.total_tokens: int = 0
        self.estimated_cost_yen: float = 0.0

    def add_usage(self, prompt_tokens: int, completion_tokens: int, rate_per_1k_yen: float = 0.0003) -> None:
        usage = prompt_tokens + completion_tokens
        self.total_tokens += usage
        self.estimated_cost_yen += (usage / 1000.0) * rate_per_1k_yen

        if self.total_tokens > self.config.max_tokens_per_episode:
            raise CostBudgetExceededError(
                f"トークン上限超過: {self.total_tokens} > {self.config.max_tokens_per_episode}"
            )
        if self.estimated_cost_yen > self.config.max_cost_yen_per_episode:
            raise CostBudgetExceededError(
                f"コスト上限超過: {self.estimated_cost_yen:.2f}円 > {self.config.max_cost_yen_per_episode}円"
            )

    def is_within_budget(self) -> bool:
        return (
            self.total_tokens <= self.config.max_tokens_per_episode
            and self.estimated_cost_yen <= self.config.max_cost_yen_per_episode
        )
