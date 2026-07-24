"""
streamlit_app/sidebar_sections/book_manager.py - 作品管理・選択セクション
"""
from __future__ import annotations

import streamlit as st
from src.engine_service import EngineService
from streamlit_app.state import UIStateStore, get_session

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

        book_ids = [b.id for b in books]
        book_opts = {b.id: f"[{b.id}] {b.title}" for b in books}

        session = get_session()
        current_id = session.current_book_id
        default_idx = 0
        if current_id in book_ids:
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
                "🔴" if stress >= STRESS_THRESHOLD_HIGH
                else "🟡" if stress >= STRESS_THRESHOLD_MEDIUM
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
