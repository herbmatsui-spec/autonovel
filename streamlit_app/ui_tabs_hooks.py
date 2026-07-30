"""
ui_tabs_hooks.py - 章末フック診断のStreamlit UI

バックエンドの /api/hooks エンドポイントと通信し、
各章のフック強度の可視化・弱いフックの修正案生成を提供する。
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def _fetch_diagnosis(book_id: int) -> Dict[str, Any]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", f"/hooks/books/{book_id}/diagnose") or {}
    except Exception as exc:  # noqa: BLE001
        st.error(f"診断の取得に失敗しました: {exc}")
        return {}


def _fetch_suggestion(book_id: int, ep_num: int, api_key: str) -> str:
    try:
        from streamlit_app.api_client import _request

        data = _request("POST", f"/hooks/books/{book_id}/suggest", api_key=api_key, ep_num=ep_num)
        return data.get("suggestion", "") if data else ""
    except Exception as exc:  # noqa: BLE001
        st.error(f"修正案の生成に失敗しました: {exc}")
        return ""


def _apply_fix(book_id: int, ep_num: int, content: str) -> None:
    try:
        from streamlit_app.api_client import _request

        _request("POST", f"/hooks/books/{book_id}/episodes/{ep_num}/apply", content=content)
        st.toast("修正案を適用しました", icon="✔")
    except Exception as exc:  # noqa: BLE001
        st.error(f"適用に失敗しました: {exc}")


def render_hooks_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_HOOK

    st.header(f"{ICON_HOOK} 章末フック診断")
    st.write(
        "各章の文末が「続きを読みたい」欲求（フック）をどの程度持っているかを診断します。"
        "閾値を下回る章は、読者の離脱リスクが高いため、修正案を生成して強化できます。"
    )

    diag = _fetch_diagnosis(book_id)
    if not diag:
        st.info("まだ章が生成されていないか、診断データを取得できませんでした。")
        return

    threshold = diag.get("threshold", 0.7)
    scores: List[Dict[str, Any]] = diag.get("scores", [])
    st.metric("弱いフックの章", f"{diag.get('weak_count', 0)} / {diag.get('total', 0)}")

    api_key = state.get("api_key") or ""

    for s in scores:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**第{s['ep_num']}話** {s.get('title') or ''}")
                st.progress(min(max(s["hook_score"], 0.0), 1.0))
                st.caption(f"フックスコア: {s['hook_score']} （閾値 {threshold}）")
            with c2:
                if s["is_weak"]:
                    if st.button("💡 修正案を生成", key=f"hook_gen_{s['ep_num']}", use_container_width=True):
                        if not api_key:
                            st.warning("APIキーが未設定です（サイドバーで入力）。")
                        else:
                            with st.spinner("修正案を生成中..."):
                                sugg = _fetch_suggestion(book_id, s["ep_num"], api_key)
                            if sugg:
                                st.session_state[f"hook_sugg_{s['ep_num']}"] = sugg
                                st.rerun()
                else:
                    st.success("良好")

            sugg = st.session_state.get(f"hook_sugg_{s['ep_num']}")
            if sugg:
                st.markdown("**💡 修正案（章末）**")
                st.write(sugg)
                if st.button("✔ この修正案を適用", key=f"hook_apply_{s['ep_num']}", use_container_width=True):
                    _apply_fix(book_id, s["ep_num"], sugg)
                    st.rerun()
