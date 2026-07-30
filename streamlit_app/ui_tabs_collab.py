"""
ui_tabs_collab.py - 共同執筆・レビューコメントのStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def _get(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("GET", path, **kw)


def _post(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("POST", path, **kw)


def _patch(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("PATCH", path, **kw)


def _delete(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("DELETE", path, **kw)


def render_collab_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_COLLAB

    st.header(f"{ICON_COLLAB} 共同編集・レビューコメント")
    st.write(
        "複数の編集者が章にコメントを付けてレビューできます。"
        "未解決のコメントを「解決済み」に切り替えながら、品質を向上させます。"
    )

    # メンバー管理
    with st.expander("👤 メンバー管理", expanded=False):
        members = _get(f"/collab/books/{book_id}/members") or []
        for m in members:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"- **{m['user_name']}** ({m['role']})")
            if c2.button("削除", key=f"mem_del_{m['id']}"):
                _delete(f"/collab/books/{book_id}/members/{m['id']}")
                st.rerun()
        with st.form("add_member", border=True):
            name = st.text_input("ユーザー名")
            role = st.selectbox("権限", ["owner", "editor", "viewer"])
            if st.form_submit_button("メンバー追加"):
                if name:
                    _post(f"/collab/books/{book_id}/members", user_name=name, role=role)
                    st.rerun()

    # コメント
    st.subheader("💬 レビューコメント")
    ep = st.number_input("対象章番号", min_value=1, step=1, value=1)
    with st.form("add_comment", border=True):
        author = st.text_input("投稿者名", value="編集者A")
        anchor = st.text_input("アンカー文（任意）", placeholder="引用する該当箇所")
        content = st.text_area("コメント内容")
        if st.form_submit_button("コメント投稿"):
            if content.strip():
                _post(
                    f"/collab/books/{book_id}/chapters/{ep}/comments",
                    author_name=author,
                    content=content,
                    anchor_text=anchor,
                )
                st.rerun()

    comments = _get(f"/collab/books/{book_id}/comments", chapter_ep=ep) or []
    if not comments:
        st.info("この章にはまだコメントがありません。")
    for c in comments:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                if c.get("anchor_text"):
                    st.caption(f"引用: 「{c['anchor_text']}」")
                st.markdown(f"**{c['author_name']}**: {c['content']}")
                st.caption(f"解決: {'✔' if c['resolved'] else '未'}")
            with c2:
                if not c["resolved"]:
                    if st.button("✔ 解決", key=f"cm_res_{c['id']}"):
                        _patch(f"/comments/{c['id']}/resolve", resolved=True)
                        st.rerun()
                else:
                    if st.button("↺ 未解決", key=f"cm_reopen_{c['id']}"):
                        _patch(f"/comments/{c['id']}/resolve", resolved=False)
                        st.rerun()
                if st.button("🗑", key=f"cm_del_{c['id']}"):
                    _delete(f"/comments/{c['id']}")
                    st.rerun()
