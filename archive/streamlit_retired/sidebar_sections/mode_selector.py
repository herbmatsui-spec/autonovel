"""
streamlit_app/sidebar_sections/mode_selector.py - モード選択セクション
"""
from __future__ import annotations

import streamlit as st
from streamlit_app.state import UIStateStore
from streamlit_app.ui.icons import ICON_PLANNING, ICON_SETTINGS

def render_mode_selector() -> None:
    """アプリの動作モード（かんたん/上級者）選択ラジオボタンを描画する。"""
    mode_descriptions = {
        "easy": "AIプロデューサーのガイドに従って、対話形式でサクッと物語を構築します。初心者の方や、アイデアを素早く形にしたい方に最適です。",
        "advanced": "プロットの構造や詳細設定を自在にコントロールし、こだわり抜いた設計を行います。物語の構成に精通した方や、緻密な設計を好む方に最適です。",
    }

    mode_labels = {
        "easy": f"{ICON_PLANNING} かんたんモード",
        "advanced": f"{ICON_SETTINGS} 上級者モード",
    }
    current_mode = UIStateStore.get_runtime().app_mode

    new_mode = st.radio(
        "あなたに合ったスタイルを選択してください",
        list(mode_labels.keys()),
        index=list(mode_labels.keys()).index(current_mode) if current_mode in mode_labels else 0,
        format_func=lambda k: mode_labels[k],
    )

    st.info(mode_descriptions.get(new_mode, ""))

    if new_mode != current_mode:
        UIStateStore.get_runtime().app_mode = new_mode
        st.rerun()
