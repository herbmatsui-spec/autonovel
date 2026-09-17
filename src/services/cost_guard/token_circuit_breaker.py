"""1話あたりコスト/トークン上限サーキットブレーカー (v5.0 Step 20).

LLMの予期せぬ無限ループや異常な大量トークン消費を瞬時に検知し、
設定した予算上限（例: 50,000トークン / 15円）を超えた瞬間に処理を自動遮断する安全保護装置。
"""
from __future__ import annotations


class BudgetExceededError(Exception):
    """トークンまたはコストの予算上限を超過した際の例外。"""

    pass


class TokenCircuitBreaker:
    """1話あたりの暴走・無限ループ課金を防止するサーキットブレーカー。"""

    def __init__(
        self,
        max_tokens_per_episode: int = 50_000,
        max_cost_jpy_per_episode: float = 15.0,
    ):
        self.max_tokens = max_tokens_per_episode
        self.max_cost_jpy = max_cost_jpy_per_episode
        self.accumulated_tokens = 0
        self.accumulated_cost_jpy = 0.0

    def record_usage(self, tokens: int, cost_jpy: float) -> None:
        """トークンおよびコストを累計し、閾値超過時に即座に遮断例外を送出する。"""
        self.accumulated_tokens += tokens
        self.accumulated_cost_jpy += cost_jpy

        if self.accumulated_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.accumulated_tokens} > {self.max_tokens}"
            )
        if self.accumulated_cost_jpy > self.max_cost_jpy:
            raise BudgetExceededError(
                f"Cost budget exceeded: {self.accumulated_cost_jpy:.2f} JPY > {self.max_cost_jpy:.2f} JPY"
            )

    def reset(self) -> None:
        """エピソード開始時にカウンタを初期化する。"""
        self.accumulated_tokens = 0
        self.accumulated_cost_jpy = 0.0
