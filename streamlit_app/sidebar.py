"""
sidebar.py - アプリケーションのサイドバー描画および作品管理UI (オーケストレーター)
"""
from __future__ import annotations

import streamlit as st

from streamlit_app.sidebar_sections.api_key import render_api_key_section
from streamlit_app.sidebar_sections.book_manager import render_book_selector
from streamlit_app.sidebar_sections.mode_selector import render_mode_selector
from streamlit_app.sidebar_sections.token_usage import render_token_usage
from streamlit_app.sidebar_sections.writing_params import render_sidebar_settings
from streamlit_app.state import UIStateStore, get_session

def render_sidebar(engine_ready: bool = False) -> str | None:
    UIStateStore.increment_rerun_count()

    with st.sidebar:
        st.caption(f"🔄 Rerun Count: {UIStateStore.get_rerun_count()}")
        st.title("⚔️ 覇権小説エンジン v3.0")
        st.caption("カクヨムランキング1位を狙う全自動執筆ツール")

    session = get_session()

    st.markdown("### ⚙️ システム設定")
    api_key, is_key_valid = render_api_key_section(session)

    if not api_key or not is_key_valid:
        st.warning("有効なAPIキーを入力し、確定ボタンを押してください。")
        return None

    st.divider()

    st.markdown("### 🎮 操作モード")
    render_mode_selector()

    st.divider()

    st.markdown("### 🛠️ 執筆パラメータ")
    render_sidebar_settings()

    st.divider()

    st.markdown("### 💰 リソース状況")
    render_token_usage()

    return api_key

# 後方互換性の再エクスポート
__all__ = ["render_sidebar", "render_book_selector"]
