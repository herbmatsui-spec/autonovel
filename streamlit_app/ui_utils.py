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
    <div style="text-align:center; padding: 2rem 0;">
        <h1>{title}</h1>
        <p style="color:#666;">{subtitle}</p>
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
    .roadmap-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        padding: 1rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .roadmap-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        flex: 1;
    }
    .step-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #f0f2f6;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 1.2rem;
        border: 2px solid #ccc;
        z-index: 2;
        transition: all 0.3s ease;
    }
    .step-label {
        margin-top: 0.5rem;
        font-size: 0.8rem;
        color: #666;
        font-weight: bold;
    }
    .roadmap-step.active .step-icon {
        background: linear-gradient(135deg, #e94560 0%, #ff6b81 100%);
        color: white;
        border-color: #e94560;
        box-shadow: 0 0 15px rgba(233, 69, 96, 0.6);
        transform: scale(1.1);
    }
    .roadmap-step.active .step-label {
        color: #e94560;
    }
    .roadmap-step.completed .step-icon {
        background: linear-gradient(135deg, #4caf50 0%, #8bc34a 100%);
        color: white;
        border-color: #4caf50;
    }
    .roadmap-line {
        position: absolute;
        top: 20px;
        left: 50%;
        width: 100%;
        height: 3px;
        background: linear-gradient(to right, #ccc, #eee);
        z-index: 1;
    }
    .roadmap-step:last-child .roadmap-line {
        display: none;
    }
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
