"""モデル別トークン単価・コスト計算エンジン (v5.0 Step 19).

各LLMモデル（Gemini 2.5 Flash, Claude Haiku, GPT-4o mini等）の入出力トークン消費から
1話あたりのリアルタイムコスト（USD / JPY）を精密計算する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

# 1M (1,000,000) トークンあたりの価格 (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
}

USD_JPY_RATE = 150.0


@dataclass
class CostEstimate:
    """コスト見積もり結果。"""

    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    cost_jpy: float


class BudgetCalculator:
    """トークン消費量とモデル価格表に基づくコスト計算クラス。"""

    @classmethod
    def calculate_cost(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CostEstimate:
        """モデル名とトークン数からコスト（USD / JPY）を算出する。"""
        pricing = MODEL_PRICING.get(model, {"input": 0.15, "output": 0.60})
        cost_usd = (prompt_tokens / 1_000_000.0) * pricing["input"] + (
            completion_tokens / 1_000_000.0
        ) * pricing["output"]
        cost_jpy = cost_usd * USD_JPY_RATE

        return CostEstimate(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost_usd, 6),
            cost_jpy=round(cost_jpy, 4),
        )
