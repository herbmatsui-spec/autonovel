"""ページ定義モジュール

st.Page オブジェクトを定義し、ナビゲーション構造を管理します。
"""

import streamlit as st

from src.engine_service import EngineService
from streamlit_app.landing import render_help_tab as _render_help_tab
from streamlit_app.landing import render_landing as _render_landing
from streamlit_app.sidebar import render_book_selector as _select_book
from streamlit_app.state import UIStateStore
from streamlit_app.ui_components import progress_fragment
from streamlit_app.ui_tabs_analytics import (
    render_prompt_metrics_dashboard,
    render_strategy_tab,
    render_style_lab_tab,
)
from streamlit_app.ui_tabs_audit import render_audit_tab
from streamlit_app.ui_tabs_marketing import render_promo_tab
from streamlit_app.ui_tabs_monitor import render_monitor_tab
from streamlit_app.ui_tabs_planning import render_planning_tab
from streamlit_app.ui_tabs_writing import (
    render_import_tab,
    render_plot_tab,
    render_rebuild_tab,
    render_writing_tab,
)

# 共通エラー・警告メッセージ定数
MSG_SELECT_BOOK_FIRST = "👈 まず「企画立案」タブから作品を生成するか、サイドバーで作品を選択してください。"

def _get_engine():
    # api_key is already in session if we reached here
    return EngineService.get_instance()

def _wrap_easy_mode():
    state = UIStateStore.get_runtime_state()
    engine = _get_engine()
    progress_fragment("easy_job", engine=engine)
    # render_easy_mode is now in ui_tabs_planning.py, but this is a wrapper for a page.
    from streamlit_app.ui_tabs_planning import render_easy_mode
    render_easy_mode(state, engine)

def _make_tab_wrapper(render_func, requires_book: bool = True, passes_state: bool = True):
    """
    タブのラッパー関数を生成する高階関数。
    重複コードを排除し、状態取得、エンジン取得、進捗表示、作品選択の共通フローをカプセル化する。
    """
    def wrapper():
        engine = _get_engine()
        progress_fragment("global_job", engine=engine)

        book_id = None
        if requires_book or render_func in (render_planning_tab, render_style_lab_tab):
            book_id = _select_book(engine)
            if requires_book and book_id is None:
                st.info(MSG_SELECT_BOOK_FIRST)
                return

        args = []
        if passes_state:
            state = UIStateStore.get_runtime_state()
            args.append(state)
        args.append(engine)
        if requires_book:
            args.append(book_id)

        render_func(*args)
    return wrapper

# 共通ラッパーファクトリを利用したタブ定義
_wrap_planning_tab = _make_tab_wrapper(render_planning_tab, requires_book=False, passes_state=True)
_wrap_plot_tab     = _make_tab_wrapper(render_plot_tab,     requires_book=True,  passes_state=True)
_wrap_writing_tab  = _make_tab_wrapper(render_writing_tab,  requires_book=True,  passes_state=True)
_wrap_monitor_tab  = _make_tab_wrapper(render_monitor_tab,  requires_book=True,  passes_state=True)
_wrap_audit_tab    = _make_tab_wrapper(render_audit_tab,    requires_book=True,  passes_state=True)
_wrap_import_tab   = _make_tab_wrapper(render_import_tab,   requires_book=True,  passes_state=False)
_wrap_style_lab_tab = _make_tab_wrapper(render_style_lab_tab, requires_book=False, passes_state=False)
_wrap_strategy_tab = _make_tab_wrapper(render_strategy_tab, requires_book=True,  passes_state=False)
_wrap_promo_tab    = _make_tab_wrapper(render_promo_tab,    requires_book=True,  passes_state=True)
_wrap_rebuild_tab  = _make_tab_wrapper(render_rebuild_tab,  requires_book=True,  passes_state=False)
_wrap_metrics_tab  = _make_tab_wrapper(render_prompt_metrics_dashboard, requires_book=False, passes_state=False)


def get_pages():
    """アプリケーションモードに応じたページ構成を返す"""

    # 共通ページ（モードに関わらず表示）
    landing_page = st.Page(
        _render_landing,
        title="ホーム",
        icon="🚀",
        url_path="landing",
        default=True,
    )

    easy_mode_page = st.Page(
        _wrap_easy_mode,
        title="かんたんモード",
        icon="⚡",
        url_path="easy",
    )

    help_page = st.Page(
        _render_help_tab,
        title="ヘルプ・使い方",
        icon="❓",
        url_path="help",
    )

    # 上級者モードのページ群
    planning_page = st.Page(
        _wrap_planning_tab,
        title="企画立案",
        icon="📋",
        url_path="planning",
    )

    plot_page = st.Page(
        _wrap_plot_tab,
        title="プロット設計",
        icon="📖",
        url_path="plot",
    )

    writing_page = st.Page(
        _wrap_writing_tab,
        title="本文執筆",
        icon="✍️",
        url_path="writing",
    )

    monitor_page = st.Page(
        _wrap_monitor_tab,
        title="進捗モニター",
        icon="📈",
        url_path="monitor",
    )

    audit_page = st.Page(
        _wrap_audit_tab,
        title="品質監査",
        icon="⚖️",
        url_path="audit",
    )

    import_page = st.Page(
        _wrap_import_tab,
        title="インポート",
        icon="📥",
        url_path="import",
    )

    style_lab_page = st.Page(
        _wrap_style_lab_tab,
        title="文体ラボ",
        icon="🧬",
        url_path="style-lab",
    )

    strategy_page = st.Page(
        _wrap_strategy_tab,
        title="戦略分析",
        icon="📈",
        url_path="strategy",
    )

    promo_page = st.Page(
        _wrap_promo_tab,
        title="宣伝・マーケ",
        icon="📢",
        url_path="promo",
    )

    rebuild_page = st.Page(
        _wrap_rebuild_tab,
        title="プロット再構築",
        icon="🔨",
        url_path="rebuild",
    )

    metrics_page = st.Page(
        _wrap_metrics_tab,
        title="メトリクス",
        icon="📊",
        url_path="metrics",
    )

    # モード別のページグループ
    easy_pages = [landing_page, easy_mode_page, help_page]

    advanced_pages = [
        landing_page,
        planning_page,
        plot_page,
        writing_page,
        monitor_page,
        audit_page,
        import_page,
        style_lab_page,
        strategy_page,
        promo_page,
        rebuild_page,
        metrics_page,
        help_page,
    ]

    return {
        "かんたんモード": easy_pages,
        "上級者モード": advanced_pages,
    }
