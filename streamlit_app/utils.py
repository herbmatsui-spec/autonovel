"""Streamlit UI 層専用のユーティリティ。"""

from src.shared.utils import estimate_tokens, COST_INPUT_FLASH, COST_OUTPUT_FLASH


def display_cost_estimate(text: str, label: str = "内容") -> None:
    """Streamlit 上にトークン数と推定コストをキャプション表示する"""
    import streamlit as st

    tokens = estimate_tokens(text)
    avg_rate = (COST_INPUT_FLASH + COST_OUTPUT_FLASH) / 2
    cost = tokens * avg_rate
    st.caption(f"{label} 推定トークン: {tokens} (概算コスト: ${cost:.6f})")
