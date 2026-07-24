"""
landing.py - アプリケーションのランディングページおよびヘルプマニュアルの描画
"""
from __future__ import annotations

import streamlit as st
from streamlit_app.ui.icons import ICON_ANALYTICS, ICON_PLANNING, ICON_WRITING, ICON_MONITOR


def render_landing() -> None:
    """ランディングページ（APIキー未入力時）を表示する"""
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">異世界小説生成プラットフォーム</h1>
        <p style="font-size: 1.2rem; color: #cbd5e1; margin-top: 1rem;">
            あなたの想像力を、プロ品質の文章とロジカルなプロットに高速変換。
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.info("👈 開始するには、左側のサイドバーに **Gemini API キー** を入力し、「確定」ボタンを押してください。")

    st.markdown("### ✨ 主な機能")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_PLANNING}</span>
            <h3>高度な物語設計</h3>
            <p class="text-muted">独自の感情解析アルゴリズムが、読者の心を掴む展開やカタルシスのタイミングを精密計算。</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_WRITING}</span>
            <h3>プロ品質のAI執筆</h3>
            <p class="text-muted">最新のAIモデルを搭載し、数千文字におよぶ高精細な情景・心理描写を自動生成。</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_ANALYTICS}</span>
            <h3>市場トレンド最適化</h3>
            <p class="text-muted">現在のウェブ小説トレンドを分析し、バズるキーワードやフックをAIプロデューサーが提案。</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🚀 ご利用の流れ")
    col_step1, col_step2, col_step3 = st.columns(3)
    with col_step1:
        with st.container(border=True):
            st.markdown(f"#### {ICON_PLANNING} 1. 企画・設計")
            st.caption("AIと共にジャンルや登場人物、物語の骨組みを構築します。")
    with col_step2:
        with st.container(border=True):
            st.markdown(f"#### {ICON_WRITING} 2. 高速執筆")
            st.caption("ボタンひとつで章ごとの詳細プロットと本文を自動執筆します。")
    with col_step3:
        with st.container(border=True):
            st.markdown(f"#### {ICON_MONITOR} 3. 監査・出力")
            st.caption("感情曲線をチェックし、推敲を重ねて完成原稿を出力します。")

    st.markdown("""
        <footer class="app-footer">
            <p>© 2026 覇権小説エンジン Project. All rights reserved.</p>
        </footer>
    """, unsafe_allow_html=True)


def render_help_tab() -> None:
    """ヘルプ・マニュアルを表示"""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = f.read()
        st.markdown(readme_content)
    except FileNotFoundError:
        st.error("README.md が見つかりません。")
