from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def render_novel_production_tab(
    state: Optional[Dict[str, Any]] = None,
    engine: Optional[Any] = None,
    book_id: Optional[int] = None,
) -> None:
    """小説制作統合タブ。クリック時に /api/commercial/run を呼び出し、rerun を発火する。"""
    if state is None:
        state = {}
    if st.button("commercial_run"):
        _call_commercial_api(book_id=book_id)
        st.rerun()


def _call_commercial_api(book_id: Optional[int] = None) -> None:
    """商用化パイプライン (/api/commercial/run) を呼び出す。"""
    try:
        from streamlit_app.api_client import run_commercial_pipeline

        run_commercial_pipeline(
            series_config={"book_id": book_id} if book_id else {},
            samples=[],
            platforms=[],
            timeout=180.0,
        )
    except Exception as exc:
        logger.warning("Commercial pipeline call failed: %s", exc)


def render_plot_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    render_novel_production_tab(state, engine, book_id)


def render_writing_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    render_novel_production_tab(state, engine, book_id)


def render_import_tab(engine: Any, book_id: int) -> None:
    render_novel_production_tab({}, engine, book_id)


def render_rebuild_tab(engine: Any, book_id: int) -> None:
    render_novel_production_tab({}, engine, book_id)
