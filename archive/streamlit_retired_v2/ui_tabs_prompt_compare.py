"""
ui_tabs_prompt_compare.py - ジャンル別プロンプト A/B 比較のStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def _get(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("GET", path, **kw)


def _post(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("POST", path, **kw)


def render_prompt_compare_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_COMPARE

    st.header(f"{ICON_COMPARE} プロンプト A/B 比較")
    st.write(
        "同一の評価文に対して複数のプロンプトバージョンの出力を比較し、"
        "品質スコア（フック/リズム/一貫性/商業性/感情共鳴/整合性）の合計で勝者を決定します。"
    )

    prompt_key = st.text_input("プロンプトキー", value="writing_style")
    if st.button("📥 バージョンを読み込む", use_container_width=True):
        versions = _get(f"/prompt-compare/books/{book_id}/versions", prompt_key=prompt_key)
        if versions:
            st.session_state["pc_versions"] = versions
            st.rerun()

    versions = st.session_state.get("pc_versions", [])
    if not versions:
        st.info("まずバージョンを読み込むか、評価文を直接入力してください。")
        return

    st.markdown(f"**読み込み済みバージョン: {len(versions)} 件**")
    texts: List[str] = []
    for v in versions:
        texts.append(st.text_area(f"出力（{v['version_tag']}）", key=f"pc_text_{v['id']}", height=150))

    if st.button("⚖️ 比較実行", use_container_width=True):
        if any(t.strip() for t in texts):
            with st.spinner("評価中..."):
                result = _post(
                    f"/prompt-compare/books/{book_id}/compare",
                    prompt_key=prompt_key, texts=texts,
                )
            if result:
                st.subheader("🏆 結果")
                winner = result.get("winner", {})
                st.success(f"勝者: {winner.get('winner_label')}（理由: {winner.get('reason')}）")
                for r in result.get("results", []):
                    with st.expander(f"{r['label']} — 合計 {r['weighted_total']}"):
                        for k, v in r["scores"].items():
                            st.markdown(f"- {k}: {v}")
                        st.caption(r["output_preview"])
        else:
            st.warning("各バージョンの出力を入力してください。")
