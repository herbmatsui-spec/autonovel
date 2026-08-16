"""
ui_tabs_structure.py - 物語構造テンプレート検証のStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def _fetch_templates() -> List[Dict[str, Any]]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", "/structure/templates") or []
    except Exception:  # noqa: BLE001
        return [{"key": "three_act", "name": "三幕構成"}]


def _fetch_validation(book_id: int, structure: str) -> Dict[str, Any]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", f"/structure/books/{book_id}/validate?structure={structure}") or {}
    except Exception as exc:  # noqa: BLE001
        st.error(f"検証に失敗しました: {exc}")
        return {}


def render_structure_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_STRUCTURE

    st.header(f"{ICON_STRUCTURE} 物語構造診断")
    st.write(
        "三幕構成・起承転結・ヒーローズジャーニー等のテンプレートと照合し、"
        "不足しているビートやクライマックスの位置のずれを検出します。"
    )

    templates = _fetch_templates()
    structure = st.selectbox(
        "構造テンプレート",
        options=[t["key"] for t in templates],
        format_func=lambda x: next((t["name"] for t in templates if t["key"] == x), x),
    )

    if st.button("🔍 構造を検証", use_container_width=True):
        with st.spinner("検証中..."):
            report = _fetch_validation(book_id, structure)
        if not report:
            st.info("プロットが存在しません。")
            return

        st.subheader(f"結果: {report.get('structure')}（{report.get('total_chapters')}話）")
        if report.get("is_healthy"):
            st.success("✅ 構造は健全です")
        else:
            st.warning("⚠️ 改善の余地があります")

        missing = report.get("missing_beats", [])
        if missing:
            st.markdown("**不足しているビート:**")
            for b in missing:
                st.markdown(f"- ❌ {b['label']}（想定位置: 約 {int(b['expected_phase']*100)}% 付近）")
        else:
            st.markdown("**必須ビート:** ✅ すべて揃っています")

        climax = report.get("climax", {})
        st.markdown(f"**クライマックス位置:** {'✅' if climax.get('ok') else '⚠️'} {climax.get('reason', '')}")

        pacing = report.get("pacing", {})
        st.markdown(f"**ペーシング:** {'✅' if pacing.get('ok') else '⚠️'} {pacing.get('reason', '')}")
