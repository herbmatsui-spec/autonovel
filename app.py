"""
app.py - 覇権小説自動生成ツール v3.0 エントリーポイント

【実装済み改善案】
  案1: かんたんモード（全自動） — ジャンル選択 + ボタン1つで全工程自動実行
  案2: 4ステップウィザード   — 初心者が迷わない段階的UI
  案6: ストレス感情曲線ループ  — 累積ストレスを監視し自動でカタルシスを発動

起動方法:
    streamlit run app.py

必要ライブラリ:
    pip install streamlit google-genai aiosqlite pydantic jinja2
"""
from __future__ import annotations
import warnings
import logging

import streamlit as st

# ==========================================
# アプリ初期化（set_page_config は最初に1回だけ）
# ==========================================
try:
    st.set_page_config(
        page_title="覇権小説エンジン v3.0",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)

from google import genai
from config import GlobalConfig
from database import get_db_manager
from engine import UltimateHegemonyEngine, safe_run_async
from background import run_in_background, TokenUsageTracker
from ui_components import (
    inject_focus_css,
    progress_fragment,
    render_easy_mode,
    render_planning_tab,
    render_plot_tab,
    render_writing_tab,
    render_import_tab,
    render_style_lab_tab,
    render_strategy_tab,
    render_promo_tab,
    render_rebuild_tab,
)

@st.cache_resource
def get_genai_client(api_key: str):
    """SDKクライアントを個別にキャッシュし、内部スレッドの乱立を防ぐ"""
    return genai.Client(api_key=api_key)

@st.cache_resource
def get_hegemony_engine(api_key: str):
    client = get_genai_client(api_key)
    return UltimateHegemonyEngine(api_key=api_key, client=client, db_manager=get_db_manager())


# ==========================================
# セッション初期化
# ==========================================
def _init_session() -> None:
    defaults = {
        "token_stats":        {"prompt": 0, "completion": 0, "calls": 0},
        "forbidden_patterns": [],
        "selected_desires":   ["カタルシス"],
        "app_mode":           "easy",   # "easy" or "advanced"
        "current_book_id":    None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ==========================================
# サイドバー
# ==========================================
def _render_sidebar(engine_ready: bool = False) -> str | None:
    st.sidebar.title("⚔️ 覇権小説エンジン v3.0")
    st.sidebar.caption("カクヨムランキング1位を狙う全自動執筆ツール")

    api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password", key="api_key_input")
    if api_key:
        st.session_state["api_key"] = api_key

    current_key = st.session_state.get("api_key", "")
    if not current_key:
        st.sidebar.warning("APIキーを入力してください。")
        return None

    st.sidebar.divider()

    # ── モード切り替え ──
    st.sidebar.subheader("🎮 モード選択")
    mode_labels = {"easy": "🚀 かんたんモード", "advanced": "⚙️ 上級者モード"}
    new_mode = st.sidebar.radio(
        "使い方を選択",
        list(mode_labels.keys()),
        format_func=lambda k: mode_labels[k],
        index=0 if st.session_state.app_mode == "easy" else 1,
        key="mode_radio",
    )
    if new_mode != st.session_state.app_mode:
        st.session_state.app_mode = new_mode
        st.rerun()

    st.sidebar.divider()

    # ── 集中執筆モード ──
    if st.sidebar.toggle("🖋️ 集中執筆モード（明朝体）", value=False):
        inject_focus_css()

    # ── 禁止表現設定 ──
    with st.sidebar.expander("🚫 禁止表現設定"):
        forbidden_input = st.text_area(
            "禁止したい表現（1行1つ）",
            value="\n".join(st.session_state.forbidden_patterns),
            height=80,
        )
        st.session_state.forbidden_patterns = [
            line.strip() for line in forbidden_input.split("\n") if line.strip()
        ]

    # ── 読者欲望設定 ──
    with st.sidebar.expander("❤️ 読者欲望設定"):
        desires = st.multiselect(
            "ターゲット読者が求めるもの",
            ["カタルシス", "ざまぁ", "萌え", "恐怖", "感動", "笑い", "謎解き", "成り上がり"],
            default=st.session_state.selected_desires,
        )
        st.session_state.selected_desires = desires

    # ── 詳細設定 ──
    with st.sidebar.expander("⚙️ 詳細設定"):
        GlobalConfig().display_sidebar()

    st.sidebar.divider()

    # ── トークン使用量 ──
    stats   = st.session_state.token_stats
    tracker = TokenUsageTracker(stats)
    st.sidebar.metric("API呼び出し回数", f"{stats['calls']}回")
    st.sidebar.metric("推定コスト",      f"${tracker.get_cost_usd():.4f}")

    return current_key


# ==========================================
# 作品選択（上級者モード用）
# ==========================================
def _select_book(engine: UltimateHegemonyEngine) -> int | None:
    books = safe_run_async(engine.repo.get_all_books())

    with st.sidebar:
        st.subheader("📚 作品管理")
        if not books:
            st.info("まだ作品がありません。企画タブから新しい作品を生成してください。")
            return None

        book_ids = [b.id for b in books]
        book_opts = {b.id: f"[{b.id}] {b.title}" for b in books}
        
        # セッション状態からインデックスを決定
        current_id = st.session_state.get("current_book_id")
        default_idx = 0
        if current_id in book_ids:
            default_idx = book_ids.index(current_id)

        selected = st.selectbox(
            "分析・執筆対象の作品を選択", 
            book_ids, 
            index=default_idx, 
            format_func=lambda x: book_opts[x],
            key="sidebar_book_selector"
        )
        st.session_state["current_book_id"] = selected

        book_detail = next((b for b in books if b.id == selected), None)
        if book_detail:
            stress = book_detail.cumulative_stress or 0
            stress_icon = "🔴" if stress >= 65 else "🟡" if stress >= 40 else "🟢"
            st.caption(f"ジャンル: {book_detail.genre}")
            st.caption(f"目標話数: {book_detail.target_eps}話")
            st.caption(f"{stress_icon} 累積ストレス: {stress}/100")

        if st.button("🗑️ この作品を削除", type="secondary"):
            safe_run_async(engine.repo.delete_book(selected))
            if st.session_state["current_book_id"] == selected:
                st.session_state["current_book_id"] = None
            st.rerun()

        return selected


# ==========================================
# かんたんモード（案1）
# ==========================================
def _render_easy_mode(engine: UltimateHegemonyEngine) -> None:
    """かんたんモード: ジャンル選択 + ボタン1つで全自動"""
    # 進捗表示（最優先で常時表示）
    progress_fragment("easy_job", engine=engine)
    render_easy_mode(engine)


# ==========================================
# 上級者モード（全タブ）
# ==========================================
def _render_advanced_mode(engine: UltimateHegemonyEngine) -> None:
    """上級者モード: 全機能への完全アクセス"""
    # 進捗表示
    progress_fragment("global_job", engine=engine)

    # 作品選択
    book_id = _select_book(engine)

    # タブ構成
    tab_names = [
        "📋 企画立案",
        "📖 プロット管理",
        "✍️ 本文執筆",
        "📥 本文インポート",
        "🧬 文体ラボ",
        "📈 戦略司令部",
        "📢 宣伝・納品",
        "🔨 プロット再構築",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        render_planning_tab(engine)

    if book_id is None:
        for tab in tabs[1:]:
            with tab:
                st.info("👈 まず「企画立案」タブから作品を生成するか、サイドバーで作品を選択してください。")
        return

    with tabs[1]:
        render_plot_tab(engine, book_id)
    with tabs[2]:
        render_writing_tab(engine, book_id)
    with tabs[3]:
        render_import_tab(engine, book_id)
    with tabs[4]:
        render_style_lab_tab(engine)
    with tabs[5]:
        render_strategy_tab(engine, book_id)
    with tabs[6]:
        render_promo_tab(engine, book_id)
    with tabs[7]:
        render_rebuild_tab(engine, book_id)


# ==========================================
# ランディングページ（APIキー未入力時）
# ==========================================
def _render_landing() -> None:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 0;">
        <h1 style="font-size:3rem;">⚔️ 覇権小説エンジン v3.0</h1>
        <p style="font-size:1.3rem; color:#888;">
            AIがカクヨムランキング1位を狙える作品を、初心者でも全自動で生成します
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### 🚀 かんたんモード
        ジャンルを選んでボタンを押すだけ。
        企画→プロット→執筆→納品まで
        **完全自動**で完結します。
        """)
    with col2:
        st.markdown("""
        ### ⚙️ 上級者モード
        文体・チート設定・感情曲線など
        全パラメータを自在にコントロール。
        **商用レベル**の細かい調整が可能。
        """)
    with col3:
        st.markdown("""
        ### 🎆 感情曲線AI
        ストレス値を自動管理し、
        最適なタイミングで「ざまぁ」を
        **自動発動**します。
        """)

    st.divider()
    st.info("👈 サイドバーに Gemini API キーを入力して開始してください。")


# ==========================================
# メイン
# ==========================================
def main() -> None:
    _init_session()

    api_key = _render_sidebar()
    if not api_key:
        _render_landing()
        return

    # エンジン初期化
    try:
        engine = get_hegemony_engine(api_key)
    except Exception as e:
        st.error(f"エンジンの初期化に失敗しました: {e}")
        return

    # モードに応じてUIを切り替え
    if st.session_state.app_mode == "easy":
        _render_easy_mode(engine)
    else:
        _render_advanced_mode(engine)


if __name__ == "__main__":
    main()
