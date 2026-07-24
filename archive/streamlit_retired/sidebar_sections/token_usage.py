"""
streamlit_app/sidebar_sections/token_usage.py - リソース・トークン使用量表示
"""
from __future__ import annotations

import streamlit as st
from streamlit_app.state import UIStateStore
from streamlit_app.utils import TokenUsageTracker

def render_token_usage() -> None:
    """トークン使用量と想定されるコストの表示。"""
    stats = UIStateStore.get_runtime().token_stats
    tracker = TokenUsageTracker(stats.model_dump() if hasattr(stats, "model_dump") else stats)
    st.metric("API呼び出し回数", f"{stats.calls}回")
    st.metric("推定コスト", f"${tracker.get_cost_usd():.4f}")
