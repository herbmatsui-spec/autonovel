"""
services/cost_analytics.py - 執筆コスト集計・予算アラート

トークン数からモデル別単価で推定USDコストを算出し、
予算超過を検知する。価格表は設定で上書き可能。
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# モデル別 単価 (USD / 1M tokens): (input, output)
# OpenRouter モデル名 (provider/model) と内部名の両方をサポート
DEFAULT_PRICING: dict[str, tuple] = {
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


def estimate_cost_usd(
    task_type: str, input_tokens: int, output_tokens: int, model: str | None = None
) -> float:
    """タスク種別をモデル名にマッピングして推定コストを算出する。"""
    effective_model = model or _task_to_model(task_type)
    in_price, out_price = DEFAULT_PRICING.get(effective_model, DEFAULT_PRICING["default"])
    return round(
        (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price, 6
    )


def _task_to_model(task_type: str) -> str:
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
