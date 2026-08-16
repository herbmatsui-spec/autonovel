"""
streamlit_app/sidebar_sections/book_manager.py - 作品管理・選択セクション
"""

from __future__ import annotations

import streamlit as st
from typing import Any, List, Dict

from src.engine_service import EngineService
from streamlit_app.state import UIStateStore, get_session
from schemas.app_state import AppStateModel

STRESS_THRESHOLD_HIGH = 65
STRESS_THRESHOLD_MEDIUM = 40


def render_book_selector(service: EngineService) -> int | None:
    """作品選択ボックスをサイドバーに描画し、選択中の作品IDを管理する。"""
    books = service.get_all_books()
    
    with st.sidebar:
        st.markdown("### 📚 作品管理")
        if not books:
            st.info("まだ作品がありません。企画タブから新しい作品を生成してください。")
            return None

        # Handle dictionary keys properly (keys are strings, values may represent ints)
        book_opts: Dict[int, str] = {}
        for b in books:
            if isinstance(b, dict):
                bid_val = b.get("id")
                if bid_val is not None:
                    try:
                        bid = int(bid_val) if not isinstance(bid_val, bool) else int(bid_val)
                    except Exception:
                        continue
                    else:
                        title_val = b.get("title", "")
                        if str(title_val):
                            book_opts[bid] = f"[{bid}] {str(title_val)}"
            else:
                bid_val = getattr(b, "id", None)
                if bid_val is not None:
                    try:
                        bid = int(bid_val) if not isinstance(bid_val, bool) else int(bid_val)
                    except Exception:
                        continue
                    else:
                        title_val = getattr(b, "title", "")
                        if str(title_val):
                            book_opts[bid] = f"[{bid}] {str(title_val)}"
        
        if not book_opts:
            st.info("まだ作品がありません。企画タブから新しい作品を生成してください。")
            return None

        book_ids: List[int] = list(book_opts.keys())
        session = get_session()
        current_id = session.current_book_id if isinstance(session.current_book_id, int) else None
        default_idx = 0
        if current_id is not None and current_id in book_ids:
            default_idx = book_ids.index(current_id)

        selected = st.selectbox(
            "執筆する作品を選択してください",
            book_ids,
            index=default_idx,
            format_func=lambda x: book_opts[x],
            key="sidebar_book_selector",
            help="現在編集・分析したい作品を切り替えます。",
        )
        session.current_book_id = selected

        detail = service.get_book_details(selected)
        if detail:
            book_detail = detail["book"]
            stress = detail["stress"]
            stress_icon = (
                "🔴"
                if stress >= STRESS_THRESHOLD_HIGH
                else "🟡"
                if stress >= STRESS_THRESHOLD_MEDIUM
                else "🟢"
            )
            st.caption(f"ジャンル: {book_detail.genre}")
            st.caption(f"目標話数: {book_detail.target_eps}話")
            st.caption(f"{stress_icon} 累積ストレス: {stress}/100")

        if st.button("🗑️ 作品を削除", type="secondary", use_container_width=True):
            service.delete_book(selected)
            if session.current_book_id == selected:
                UIStateStore.update(
                    lambda s: setattr(s, "current_book_id", None), notify_keys=["current_book_id"]
                )
            st.rerun()

        return selected