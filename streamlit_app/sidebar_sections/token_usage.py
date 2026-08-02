"""
streamlit_app/sidebar_sections/token_usage.py - リソース・トークン使用量表示
"""

from __future__ import annotations

import streamlit as st
from typing import Any

from streamlit_app.state import UIStateStore


class TokenUsageTracker:
    """Simple utility to calculate cost from token stats."""
    
    def __init__(self, stats: Any):
        self.stats = stats
        if hasattr(stats, 'model_dump'):
            self.prompt = stats.model_dump().get('prompt', 0)
            self.completion = stats.model_dump().get('completion', 0)
            self.calls = stats.model_dump().get('calls', 0)
        else:
            self.prompt = stats.get('prompt', 0) if isinstance(stats, dict) else 0
            self.completion = stats.get('completion', 0) if isinstance(stats, dict) else 0
            self.calls = stats.get('calls', 0) if isinstance(stats, dict) else 0

    def get_cost_usd(self) -> float:
        """Estimate USD cost based on token usage."""
        # Rough estimate: $0.0001 per 1K tokens (input + output)
        input_cost_per_1k = 0.00015  # $0.15 per 1M input tokens
        output_cost_per_1k = 0.0006  # $0.60 per 1M output tokens  per 1M output tokens
        prompt_cost = (self.prompt / 1000.0) * input_cost_per_1k
        completion_cost = (self.completion / 1000.0) * output_cost_per_1k
        return float(prompt_cost + completion_cost)


def render_token_usage() -> None:
    """トークン使用量と想定されるコストの表示。"""
    stats = UIStateStore.get_runtime().token_stats
    tracker = TokenUsageTracker(stats)
    st.metric("API呼び出し回数", f"{stats.calls}回")
    st.metric("推定コスト", f"${tracker.get_cost_usd():.4f}")