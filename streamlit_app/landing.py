"""
landing.py - アプリケーションのランディングページおよびヘルプマニュアルの描画
"""
from __future__ import annotations

import streamlit as st


def render_landing() -> None:
    """ランディングページ（APIキー未入力時）を表示する"""
    from streamlit_app.ui_utils import render_centered_title

    st.markdown("""

    render_centered_title(
        "異世界小説生成プラットフォーム",
        "あなたの想像力を、プロ品質の文章とロジカルなプロットに変換します。"
    )

    col1, col2, col3 = st.columns(3)
    from streamlit_app.ui.icons import ICON_ANALYTICS, ICON_PLANNING, ICON_WRITING

    with col1:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_PLANNING}</span>
            <h3>高度な物語設計</h3>
            <p class="text-muted">独自の感情解析アルゴリズムが、読者が求める「ざまぁ」のタイミングを計算。</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_WRITING}</span>
            <h3>プロ執筆AI</h3>
            <p class="text-muted">Gemini 1.5 Pro/Flashを搭載し、数千文字に及ぶ高精細な描写を生成。</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_ANALYTICS}</span>
            <h3>市場最適化</h3>
            <p class="text-muted">現在のウェブ小説トレンドを分析し、バズるキーワードをAIプロデューサーが提案。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🚀 利用の流れ")
    from streamlit_app.ui.icons import ICON_MONITOR
    st.markdown(f"""
        <div class="workflow-container">
            <div class="workflow-step">
                <span class="feature-icon">{ICON_PLANNING}</span>
                <strong>1. 企画・設計</strong><br>
                <small>AIと共に物語の骨組みを構築</small>
            </div>
            <div class="workflow-arrow">➜</div>
            <div class="workflow-step">
                <span class="feature-icon">{ICON_WRITING}</span>
                <strong>2. 高速執筆</strong><br>
                <small>プロ品質の描写を自動生成</small>
            </div>
            <div class="workflow-arrow">➜</div>
            <div class="workflow-step">
                <span class="feature-icon">{ICON_MONITOR}</span>
                <strong>3. 最適化・分析</strong><br>
                <small>感情曲線を解析し覇権へ導く</small>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🏆 実績と信頼性")
    st.markdown("""
        <div class="trust-badge-container">
            <div class="trust-badge">🚀 <strong>1,000+</strong> 以上のプロットを最適化</div>
            <div class="trust-badge">✍️ <strong>50M+</strong> 文字以上の高精細描写を生成</div>
            <div class="trust-badge">💎 <strong>Gemini 1.5 Pro</strong> 準拠の最高精度</div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # FAQ & Help Section
    st.markdown("### ❓ よくある質問とサポート")
    col_faq1, col_faq2 = st.columns(2)
    with col_faq1:
        with st.expander("どのような小説に向いていますか？"):

    st.divider()
    st.info("👈 左側のサイドバーに Gemini API キーを入力し、「確定」ボタンを押して開始してください。")

    st.markdown("""
            text-align: center;
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        .footer-links {
            margin-bottom: 1rem;
        }
        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            margin: 0 10px;
            transition: color 0.2s;
        }
        .footer-links a:hover {
            color: var(--primary-color);
        }
        </style> -->
        <footer class="app-footer">
            <div class="footer-links">
                <a href="#">利用規約</a>
                <a href="#">プライバシーポリシー</a>
                <a href="#">お問い合わせ</a>
            </div>
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
