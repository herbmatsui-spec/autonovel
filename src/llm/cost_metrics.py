from prometheus_client import Counter, Gauge, start_http_server
import time

from .cost_budget_guard import CostBudgetGuard


class CostMetrics:
    """
    コスト監視とメトリクス収集。
    """

    def __init__(self) -> None:
        self.total_spent = 0.0
        self.total_steps = 0
        self.cost_savings_ratio = 0.0
        self._start_time = time.time()

    def record_step(self, cost: float) -> None:
        """ステップごとのコストを記録"""
        self.total_spent += cost
        self.total_steps += 1

    def record_saving(self, amount: float) -> None:
        """節約額を記録"""
        self.cost_savings_ratio = min(1.0, self.cost_savings_ratio + (amount / self.total_spent) * 0.01)

    def get_metrics(self) -> Dict[str, float]:
        """メトリクス情報を取得"""
        elapsed = time.time() - self._start_time
        return {
            "total_steps": self.total_steps,
            "total_spent": round(self.total_spent, 2),
            "cost_savings_ratio": round(self.cost_savings_ratio, 4),
            "avg_cost_per_step": round(self.total_spent / self.total_steps, 2) if self.total_steps > 0 else 0,
            "elapsed_seconds": round(elapsed, 2),
        }

    def start_server(self, port: int = 8001) -> None:
        """Prometheusメトリクスサーバーを起動"""
        start_http_server(port)
