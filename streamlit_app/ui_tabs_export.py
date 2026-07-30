"""
ui_tabs_export.py - 出版フォーマット自動整形エクスポーターのStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def _fetch_platforms() -> List[Dict[str, str]]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", "/export/platforms") or []
    except Exception:  # noqa: BLE001
        return [
            {"platform": "narou", "description": "小説家になろう"},
            {"platform": "kakuyomu", "description": "カクヨム"},
            {"platform": "nocturn", "description": "Nocturn Novel"},
        ]


def _fetch_export(book_id: int, platform: str) -> Dict[str, Any]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", f"/export/books/{book_id}?platform={platform}") or {}
    except Exception as exc:  # noqa: BLE001
        st.error(f"エクスポートに失敗しました: {exc}")
        return {}


def render_export_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_EXPORT

    st.header(f"{ICON_EXPORT} 出版フォーマット出力")
    st.write(
        "各プラットフォームの投稿用フォーマット（なろう/カクヨム/Nocturne）に"
        "小説を整形して出力します。生成されたテキストをコピーして手動投稿にご利用ください。"
    )

    platforms = _fetch_platforms()
    platform = st.selectbox(
        "出力先プラットフォーム",
        options=[p["platform"] for p in platforms],
        format_func=lambda x: next((p["description"] for p in platforms if p["platform"] == x), x),
    )

    if st.button("📤 エクスポート生成", use_container_width=True):
        with st.spinner("整形中..."):
            data = _fetch_export(book_id, platform)
        if data:
            st.subheader(f"📄 {data.get('title', '')}（{platform}）")
            text = data.get("content", "")
            st.text_area("出力テキスト（コピーしてご利用ください）", text, height=400)
            st.download_button(
                "テキストをダウンロード",
                data=text,
                file_name=f"{data.get('title', 'novel')}_{platform}.txt",
                mime="text/plain",
            )
