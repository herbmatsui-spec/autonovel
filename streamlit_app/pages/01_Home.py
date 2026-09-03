"""
streamlit_app/pages/01_Home.py — ダッシュボード＆設定ホーム画面

このファイルがStreamlitアプリの最初の画面になります。
左サイドメニューから設定タブを選択できます。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.models import GlobalConfigModel
from streamlit_app.state import ConfigState, UIStateStore

st.set_page_config(
    page_title="AutoNovel - ホーム",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRESET_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemma-4-31b-it",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
    "qwen/qwen2.5-72b-instruct",
    "google/gemini-2.0-flash-001",
]

COST_MODE_OPTIONS = {
    "quality": "🧠 品質優先 (高性能モデル使用)",
    "balanced": "⚖️ バランス (品質とコストのトレードオフ)",
    "cost_priority": "💰 コスト優先 (軽量モデル使用)",
}

SAFETY_OPTIONS = {
    "BLOCK_NONE": "🔓 制限なし",
    "BLOCK_ONLY_HIGH": "⚠️ 高リスクのみブロック (推奨)",
    "BLOCK_ALL": "🔒 全リスクブロック",
}


def load_config() -> GlobalConfigModel:
    try:
        from config.project_context import get_config
        return get_config()
    except Exception:
        return GlobalConfigModel.default()


def render_sidebar_settings():
    """サイドバー設定パネル - 設定ページへの導線のみ"""
    st.sidebar.title("⚙️ 設定")
    st.sidebar.caption("詳細設定は設定ページで行います")

    if st.sidebar.button("⚙️ 設定ページを開く", use_container_width=True, type="primary"):
        st.switch_page("pages/00_Settings.py")

    st.sidebar.divider()

    # 現在の設定サマリー表示
    cfg = load_config()
    st.sidebar.markdown("**現在の設定**")
    st.sidebar.markdown(f"""
- **執筆モデル**: `{getattr(cfg, 'model_writing', 'N/A')}`
- **コストモード**: `{getattr(cfg, 'cost_mode', 'balanced')}`
- **NSFW許可**: {'✅' if getattr(cfg, 'enable_nsfw', False) else '❌'}
- **自動バックアップ**: {'✅' if getattr(cfg, 'auto_backup', True) else '❌'}
""")


def reset_to_defaults():
    """デフォルト設定にリセット（設定ページで使用）"""
    default_cfg = GlobalConfigModel.default()
    try:
        from config.project_context import set_config
        set_config(default_cfg)
    except Exception:
        pass


def render_dashboard():
    """メインダッシュボード"""
    st.title("📖 AutoNovel Dashboard")
    st.markdown("### AI小説執筆プラットフォーム")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📚 プロジェクト", "0", help="現在のプロジェクト数")
    with col2:
        st.metric("✍️ 執筆済み", "0文字", help="合計執筆文字数")
    with col3:
        st.metric("🤖 APIコスト", "¥0", help="今月のAPI使用コスト")
    with col4:
        st.metric("⚡ 処理状態", "待機中", help="現在の処理状態")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🚀 クイックスタート")
        st.markdown("""
        1. **プロット作成** - 物語の全体構成をAIが自動生成
        2. **詳細展開** - 各 章/エピソードの展開を詳細化
        3. **執筆開始** - AIが本文を自動執筆
        4. **品質チェック** - 論理的一貫性とカタルシス評価
        """)

        col_start, col_demo = st.columns(2)
        with col_start:
            if st.button("▶️ 新規プロジェクト作成", use_container_width=True, type="primary"):
                st.info("「プロット作成」ページから開始してください")
        with col_demo:
            if st.button("📖 デモ実行", use_container_width=True):
                st.info("デモ機能は準備中です")

    with col_right:
        st.subheader("⚙️ 現在の設定")
        cfg = load_config()

        st.markdown(f"""
        - **執筆モデル**: `{getattr(cfg, 'model_writing', 'N/A')}`
        - **コストモード**: `{getattr(cfg, 'cost_mode', 'balanced')}`
        - **NSFW許可**: {'✅' if getattr(cfg, 'enable_nsfw', False) else '❌'}
        - **自動バックアップ**: {'✅' if getattr(cfg, 'auto_backup', True) else '❌'}
        """)


def main():
    ConfigState.init_defaults()
    render_sidebar_settings()
    render_dashboard()


if __name__ == "__main__":
    main()
