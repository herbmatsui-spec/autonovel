"""
services/cost_analytics.py - 執筆コスト集計・予算アラート

トークン数からモデル別単価で推定USDコストを算出し、
予算超過を検知する。価格表は設定で上書き可能。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# モデル別 単価 (USD / 1M tokens): (input, output)
DEFAULT_PRICING: dict[str, tuple] = {
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.0),
    "gemini-2.0-flash": (0.10, 0.40),
    "default": (0.50, 1.50),
}


def estimate_cost_usd(task_type: str, input_tokens: int, output_tokens: int) -> float:
    """タスク種別をモデル名にマッピングして推定コストを算出する。"""
    model = _task_to_model(task_type)
    in_price, out_price = DEFAULT_PRICING.get(model, DEFAULT_PRICING["default"])
    return round((input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price, 6)


def _task_to_model(task_type: str) -> str:
    mapping = {
        "planning": "gemini-1.5-flash",
        "plot_expansion": "gemini-1.5-flash",
        "writing": "gemini-1.5-pro",
        "climax": "gemini-1.5-pro",
        "audit": "gemini-1.5-flash",
        "marketing": "gemini-1.5-flash",
    }
    return mapping.get(task_type, "default")


def check_budget_alert(total_cost_usd: float, budget_usd: float | None) -> dict[str, Any]:
    """予算アラートを判定する。"""
    if budget_usd is None or budget_usd <= 0:
        return {"enabled": False, "exceeded": False, "ratio": 0.0}
    ratio = total_cost_usd / budget_usd if budget_usd else 0.0
    return {
        "enabled": True,
        "exceeded": total_cost_usd > budget_usd,
        "ratio": round(ratio, 3),
        "remaining_usd": round(max(budget_usd - total_cost_usd, 0.0), 4),
    }
