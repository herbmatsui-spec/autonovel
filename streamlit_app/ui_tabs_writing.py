"""
src/streamlit_app/ui_tabs_writing.py — 小説生成タブコンポーネント（Streamlit セッション状態統一版）
"""
import json
import uuid
from typing import Any

import streamlit as st

from streamlit_app import api_client
from streamlit_app.state import UIStateStore

# ----------------------------------------------------------------------
# UIStateStore ヘルパー
# ----------------------------------------------------------------------
def get_ui(key: str, default: Any = None) -> Any:
    return UIStateStore().get_ui_state_value(key, default)

def set_ui(**kwargs) -> None:
    UIStateStore().update_ui_state(**kwargs)

def _ensure_ui_initialized() -> None:
    """UIStateStore 経由でタブ固有の初期値を一度だけ設定する（モジュールロード時の副作用を排除）。"""
    if get_ui("commercial_task_id", None) is None:
        set_ui(commercial_task_id=None)
    if get_ui("report_generated", None) is None:
        set_ui(report_generated=False)
    if get_ui("api_retry_state", None) is None:
        set_ui(api_retry_state={"attempts": 0, "max_attempts": 3, "backoff": 1})
    if get_ui("poll_interval", None) is None:
        set_ui(poll_interval=1)
    if get_ui("current_book_id", None) is None:
        set_ui(current_book_id=1)
    if get_ui("generation_history", None) is None:
        set_ui(generation_history=[])
    if get_ui("active_task_id", None) is None:
        set_ui(active_task_id=None)
    if get_ui("writing_progress", None) is None:
        set_ui(writing_progress={"current_ep": 0, "total": 0, "status": "idle"})

# ----------------------------------------------------------------------
# ユーティリティ：指数バックオフ付きリトライデコレータ
# ----------------------------------------------------------------------
def retry_api(func):
    """API呼び出しを行う際のリトライラッパー"""
    def wrapper(*args, **kwargs):
        state = get_ui("api_retry_state", {"attempts": 0, "max_attempts": 3, "backoff": 1})
        state["attempts"] += 1
        backoff = state["backoff"]

        try:
            return func(*args, **kwargs)
        except Exception as e:
            if state["attempts"] >= state["max_attempts"]:
                st.error(f"API呼び出しに失敗しました after {state['attempts']} 回の試行: {e}")
                raise
            st.warning(f"API呼び出し失敗（試行 {state['attempts']}/{state['max_attempts']}）。{backoff}s 後のリトライ...")
            state["backoff"] *= 2
            set_ui(api_retry_state=state)
            return func(*args, **kwargs)
    return wrapper

# ----------------------------------------------------------------------
# ページレイアウト
# ----------------------------------------------------------------------
def render_novel_production_tab():
    """小説生成タブを表示"""
    from streamlit_app.ui_tabs_writing_helpers import (
        _render_series_config_form,
        _render_commercial_pipeline,
        _render_generation_status,
        _render_episode_viewer,
    )

    st.title("小説生成")
    _ensure_ui_initialized()

    form_data = _render_series_config_form()
    _render_commercial_pipeline(form_data)
    _render_generation_status()
    _render_episode_viewer()


# ----------------------------------------------------------------------
# pages_config 互換ラッパー
# ----------------------------------------------------------------------
def render_writing_tab(state: Any = None, engine: Any = None, book_id: Any = None) -> None:
    """Advanced Mode の Writing タブ。`render_novel_production_tab` の互換エイリアス。"""
    render_novel_production_tab()


def _render_placeholder_tab(tab_name: str, state: Any = None, engine: Any = None, book_id: Any = None) -> None:
    st.title(tab_name)
    st.info(f"「{tab_name}」タブは準備中です。次期リリースで実装予定です。")


def render_plot_tab(state: Any = None, engine: Any = None, book_id: Any = None) -> None:
    _render_placeholder_tab("プロット展開")


def render_import_tab(state: Any = None, engine: Any = None, book_id: Any = None) -> None:
    _render_placeholder_tab("インポート")


def render_rebuild_tab(state: Any = None, engine: Any = None, book_id: Any = None) -> None:
    _render_placeholder_tab("再構築")


# ----------------------------------------------------------------------
# エントリーポイント
# ----------------------------------------------------------------------
if __name__ == "__main__":
    render_novel_production_tab()
