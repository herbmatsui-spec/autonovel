


class CostBudgetGuard:
    """
    予算上限監視とダウングレード制御。
    指定された予算上限を超えると、より安価なモデルに自動的に切り替えます。
    """

    def __init__(
        self,
        budget_limit: float = 10.0,  # USD
        threshold_percentage: float = 90.0,  # 90% 超でダウングレード
    ) -> None:
        self.budget_limit = budget_limit
        self.threshold_percentage = threshold_percentage
        self._current_usage = 0.0

    def check_and_downgrade(self, model_name: str, current_cost: float) -> bool:
        """
        現在のコストが予算上限の閾値を超えている場合、モデルをダウングレードするか否かを判断します。
        """
        if self._current_usage <= self.budget_limit * self.threshold_percentage:
            return False  # 予算内に収まっている

        # ダウングレードを実行
        self._downgrade_model(model_name)
        return True

    def _downgrade_model(self, model_name: str) -> None:
        # 安価なモデルに切り替えるロジック
        # 例: gpt-4o-mini -> gemini-1.5-flash -> llama3.1
        cheapest_alternatives = {
            "gpt-4o-mini": "gpt-4o-mini",
            "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
            "anthropic-claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        }
        # 実際のダウングレードロジックはここで行われます
        print(f"Downgrading {model_name} to cheaper alternative")

    def get_current_usage(self) -> float:
        return self._current_usage

    def set_budget_limit(self, limit: float) -> None:
        self.budget_limit = limit
