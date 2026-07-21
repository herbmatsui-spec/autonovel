from typing import Callable

import streamlit as st


def trigger_app_rerun():
    """アプリ全体を強制的に再描画する。フラグメント内からグローバル状態を更新した後に使用。"""
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()
def render_sidebar_section(title: str, content_func: Callable, expanded: bool = True):
    """汎用的なサイドバーのセクション表示"""
    with st.sidebar.expander(title, expanded=expanded):
        content_func()


def render_centered_title(title: str, subtitle: str):
    """中央揃えのタイトル表示"""
    st.markdown(f"""
    <div class="centered-title">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_action_card(title: str, description: str, action_func: Callable, button_label: str = "実行"):
    """アクションカードの表示"""
    with st.container(border=True):
        st.subheader(title)
        st.write(description)
        if st.button(button_label):
            action_func()


def render_visual_roadmap(active_tab_index: int) -> None:
    """
    物語作成の進捗を視覚的に表示するロードマップUI
    """
    steps = [
        {"label": "企画立案", "icon": "📋"},
        {"label": "プロット管理", "icon": "📖"},
        {"label": "本文執筆", "icon": "✍️"},
        {"label": "監査・修正", "icon": "⚖️"},
        {"label": "宣伝・納品", "icon": "📢"},
    ]

    # カスタムCSSでステップバーを構築
    st.markdown("""
    <style>
    </style>
    """, unsafe_allow_html=True)

    html_steps = "<div class='roadmap-container'>"
    for i, step in enumerate(steps):
        status_class = ""
        if i == active_tab_index:
            status_class = "active"
        elif i < active_tab_index:
            status_class = "completed"

        html_steps += f"""
        <div class='roadmap-step {status_class}'>
            <div class='roadmap-line'></div>
            <div class='step-icon'>{step['icon']}</div>
            <div class='step-label'>{step['label']}</div>
        </div>
        """
    html_steps += "</div>"

    st.markdown(html_steps, unsafe_allow_html=True)
