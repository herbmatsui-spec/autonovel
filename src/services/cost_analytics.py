from dataclasses import dataclass
from typing import Dict, Tuple, Optional

# Existing pricing definition
DEFAULT_PRICING: Dict[str, Tuple[float, float]] = {
    # OpenRouter フォーマット
    "google/gemini-2.0-flash": (0.10, 0.40),
    "google/gemini-1.5-flash": (0.075, 0.30),
    "google/gemini-1.5-pro": (1.25, 5.0),
    "anthropic/claude-3-5-sonnet-20241022": (3.0, 15.0),
    "anthropic/claude-3-5-haiku-20241022": (0.80, 4.0),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (3.0, 12.0),
    # 内部名 (直接プロバイダ利用時)
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.0),
    "gemini-2.0-flash": (0.10, 0.40),
    "default": (0.50, 1.50),
}

@dataclass
class CostCalculator:
    pricing: Optional[Dict[str, Tuple[float, float]]] = None
    
    def __post_init__(self) -> None:
        # Ensure default pricing is available
        if self.pricing is None:
            self.pricing = DEFAULT_PRICING.copy()
    
    def estimate_cost_usd(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
        """トークン数とモデルから推定コスト（USD）を計算する。"""
        effective_model = model or self._task_to_model()
        in_price, out_price = self.pricing.get(effective_model, self.pricing.get("default", (0.50, 1.50)))
        return round(
            (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price, 6
        )
    
    def _task_to_model(self, task_type: str = None) -> str:
        """タスク種別をモデル名にマッピングする（環境変数を考慮）。"""
        if task_type is None:
            task_type = os.environ.get("LLM_TASK_TYPE", "writing")
        provider = os.environ.get("LLM_PROVIDER", "").lower()
        
        if provider == "openrouter":
            mapping = {
                "planning": "google/gemini-2.0-flash",
                "plot_expansion": "google/gemini-2.0-flash",
                "writing": "anthropic/claude-3-5-sonnet-20241022",
                "climax": "anthropic/claude-3-5-sonnet-20241022",
                "audit": "google/gemini-2.0-flash",
                "marketing": "google/gemini-2.0-flash",
            }
        else:
            mapping = {
                "planning": "gemini-1.5-flash",
                "plot_expansion": "gemini-1.5-flash",
                "writing": "gemini-1.5-pro",
                "climax": "gemini-1.5-pro",
                "audit": "gemini-1.5-flash",
                "marketing": "gemini-1.5-flash",
            }
        return mapping.get(task_type, "default")


_default_calculator = CostCalculator()

def estimate_cost_usd(input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
    """トークン数とモデルから推定コスト（USD）を計算する（デフォルト計算機を使用）。"""
    return _default_calculator.estimate_cost_usd(input_tokens, output_tokens, model)


def check_budget_alert(current_cost: float, budget_limit: float) -> dict:
    """予算消費状況に基づいたアラート情報を返す。"""
    if budget_limit <= 0:
        return {"status": "unknown", "message": "Budget limit not set.", "ratio": 0.0}
    
    ratio = current_cost / budget_limit
    if ratio >= 1.0:
        return {"status": "exceeded", "message": "Budget exceeded!", "ratio": ratio}
    elif ratio >= 0.9:
        return {"status": "warning", "message": "Budget nearly exceeded (90%+).", "ratio": ratio}
    elif ratio >= 0.7:
        return {"status": "info", "message": "Budget consumption is significant (70%+).", "ratio": ratio}
    else:
        return {"status": "normal", "message": "Budget is within normal range.", "ratio": ratio}