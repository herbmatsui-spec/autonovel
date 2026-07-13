"""
landing.py - アプリケーションのランディングページおよびヘルプマニュアルの描画
"""
from __future__ import annotations

import streamlit as st


def render_landing() -> None:
    """ランディングページ（APIキー未入力時）を表示する"""
    from streamlit_app.ui_utils import render_centered_title

    st.markdown("""
        <style>
        .hero-section {
            background: linear-gradient(135deg, rgba(20, 20, 35, 0.9), rgba(40, 40, 60, 0.8)),
                        linear-gradient(to right, #1a1a2e, #16213e);
            background-size: cover;
            padding: 80px 20px;
            border-radius: 20px;
            text-align: center;
            color: white;
            margin-bottom: 40px;
            border: 1px solid var(--primary-color);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .trust-badge-container {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 2rem 0;
            flex-wrap: wrap;
        }
        .trust-badge {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 1rem 2rem;
            border-radius: 50px;
            font-size: 0.9rem;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .trust-badge strong {
            color: var(--primary-color);
        }
        .feature-card {
            padding: 1.5rem;
            border-radius: 15px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            height: 100%;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-color: var(--primary-color);
        }
        .feature-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
            display: block;
        }
        .workflow-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 2rem 1rem;
            gap: 1rem;
            text-align: center;
        }
        .workflow-step {
            flex: 1;
            padding: 1rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            position: relative;
        }
        .workflow-arrow {
            font-size: 1.5rem;
            color: var(--primary-color);
            font-weight: bold;
        }
        </style>
        <style>
        .hero-title {
            font-size: 3.5rem !important;
            font-weight: 800 !important;
            background: -webkit-linear-gradient(#fff, #e94560);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 5px;
        }
        </style>
        <div class="hero-section">
            <h1 class="hero-title">覇権小説エンジン v3.0</h1>
            <p style="font-size: 1.5rem; opacity: 0.9; margin-bottom: 1rem;">AIと共に、読者の心を支配する「覇権」を創り出す。</p>
            <div style="display: inline-block; padding: 0.5rem 1.5rem; background: var(--primary-color); border-radius: 50px; font-weight: bold; font-size: 1rem;">
                次世代ナラティブエンジニアリング・プラットフォーム
            </div>
        </div>
    """, unsafe_allow_html=True)

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
            <p style="color: var(--text-muted);">独自の感情解析アルゴリズムが、読者が求める「ざまぁ」のタイミングを計算。</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_WRITING}</span>
            <h3>プロ執筆AI</h3>
            <p style="color: var(--text-muted);">Gemini 1.5 Pro/Flashを搭載し、数千文字に及ぶ高精細な描写を生成。</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="feature-card">
            <span class="feature-icon">{ICON_ANALYTICS}</span>
            <h3>市場最適化</h3>
            <p style="color: var(--text-muted);">現在のウェブ小説トレンドを分析し、バズるキーワードをAIプロデューサーが提案。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🚀 利用の流れ")
    from streamlit_app.ui.icons import ICON_MONITOR
    st.markdown(f"""
        <div class="workflow-container">
            <div class="workflow-step">
                <span class="feature-icon">{ICON_PLANNING}</span>
                <strong style="font-size: 1.1rem;">1. 企画・設計</strong><br>
                <small style="color: var(--text-muted);">AIと共に物語の骨組みを構築</small>
            </div>
            <div class="workflow-arrow">➜</div>
            <div class="workflow-step">
                <span class="feature-icon">{ICON_WRITING}</span>
                <strong style="font-size: 1.1rem;">2. 高速執筆</strong><br>
                <small style="color: var(--text-muted);">プロ品質の描写を自動生成</small>
            </div>
            <div class="workflow-arrow">➜</div>
            <div class="workflow-step">
                <span class="feature-icon">{ICON_MONITOR}</span>
                <strong style="font-size: 1.1rem;">3. 最適化・分析</strong><br>
                <small style="color: var(--text-muted);">感情曲線を解析し覇権へ導く</small>
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
            st.write("主にWeb小説、特に異世界転生、ファンタジー、現代ダンジョンなどのジャンルに最適化されています。読者のカタルシスを最大化する構造をAIが提案します。")
        with st.expander("APIキーの料金はかかりますか？"):
            st.write("本アプリはあなたのGoogle Gemini APIキーを使用します。料金はGoogleのプランに基づきます（Flashモデルは無料枠が非常に大きいため、個人利用ではほぼ無料で運用可能です）。")
    with col_faq2:
        with st.expander("使い方がわからない場合は？"):
            st.write("右上の「ヘルプ」タブ、または以下のボタンから詳細なマニュアル（README）を確認してください。")
            if st.button("📖 詳細マニュアルを表示", use_container_width=True):
                UIStateStore().update_ui_state(active_tab="help")
        with st.expander("プロット作成に時間はかかりますか？"):
            st.write("AIプロデューサー診断から詳細プロット生成まで、通常数分で完了します。人間が数日かける作業を数分に凝縮します。")

    st.divider()
    st.info("👈 左側のサイドバーに Gemini API キーを入力し、「確定」ボタンを押して開始してください。")

    st.markdown("""
        <style>
        .app-footer {
            margin-top: 5rem;
            padding: 2rem 0;
            border-top: 1px solid var(--border);
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
        </style>
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
