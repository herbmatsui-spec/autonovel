"""
streamlit_app/sidebar_sections/api_key.py - APIキー入力セクション
"""
from __future__ import annotations

import asyncio
import streamlit as st

from streamlit_app.health_check import validate_api_key_async
from streamlit_app.state import UIStateStore, SessionManager
from streamlit_app.ui.icons import ICON_SETTINGS

def render_api_key_section(session) -> tuple[str | None, bool]:
    """APIキー入力セクションの描画とキー検証を行う。"""
    is_key_valid = UIStateStore.get_runtime().is_api_key_valid
    api_key_input = UIStateStore.get_api_key_input()

    if api_key_input is None and session.api_key:
        UIStateStore.set_api_key_input(session.api_key)
        api_key_input = session.api_key

    api_key = st.text_input(
        f"{ICON_SETTINGS} Gemini API Key",
        type="password",
        value=api_key_input or "",
        key="api_key_input",
        help="Google AI Studio (aistudio.google.com) で取得したAPIキーを入力してください。",
    )

    current_provider = UIStateStore.get_runtime().llm_provider
    provider_options = ["gemini", "openai"]
    selected_provider = st.selectbox(
        "LLM Provider",
        provider_options,
        index=provider_options.index(current_provider) if current_provider in provider_options else 0,
        help="Gemini (Google) or OpenAI",
    )
    UIStateStore.get_runtime().llm_provider = selected_provider

    if api_key != api_key_input:
        UIStateStore.set_api_key_input(api_key)
        UIStateStore.get_runtime().is_api_key_valid = False
        is_key_valid = False

    if st.button("🔑 キーを確定して開始", type="primary", use_container_width=True):
        if api_key:
            with st.spinner("APIキーを検証中..."):
                try:
                    is_valid, err_detail = asyncio.run(validate_api_key_async(api_key, selected_provider))
                    UIStateStore.get_runtime().is_api_key_valid = is_valid
                    if is_valid:
                        session.api_key = api_key.strip()
                        SessionManager.save_state(session)
                        st.success("APIキーが確定されました。")
                        st.rerun()
                    else:
                        st.error(f"無効なAPIキーです。({err_detail})" if err_detail else "無効なAPIキーです。")
                except Exception as e:
                    st.error(f"検証エラー: {e}")
        else:
            st.warning("APIキーを入力してください。")

    if not api_key and session.api_key:
        session.api_key = None
        UIStateStore.get_runtime().is_api_key_valid = False
        is_key_valid = False
        SessionManager.save_state(session)
        st.rerun()

    return session.api_key, is_key_valid
