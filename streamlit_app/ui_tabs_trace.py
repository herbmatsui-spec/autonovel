"""
ui_tabs_trace.py - 生成ログ・Trace ID 再現性レポートのStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def _get(path: str, **kw) -> Any:
    from streamlit_app.api_client import _request

    return _request("GET", path, **kw)


def render_trace_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_TRACE

    st.header(f"{ICON_TRACE} 再現性レポート")
    st.write(
        "各生成処理のプロンプトバージョン・モデル・パラメータ・入力ハッシュ・Trace ID を"
        "記録し、同一条件での再現性を証明するレポートを生成します。"
    )

    with st.form("record_run", border=True):
        st.subheader("生成実行を記録")
        task_type = st.text_input("タスク種別", value="writing")
        prompt_version = st.text_input("プロンプトバージョン", value="v1")
        model_name = st.text_input("モデル名", value="gemini-1.5-pro")
        params = st.text_input("パラメータ(JSON)", value='{"temp": 0.7}')
        trace_id = st.text_input("Trace ID（任意）", value="")
        ep = st.number_input("章番号（任意）", min_value=0, value=0, step=1)
        if st.form_submit_button("記録"):
            import json

            from streamlit_app.api_client import _request

            try:
                parsed_params = json.loads(params or "{}")
            except json.JSONDecodeError:
                parsed_params = {}
            res = _request(
                "POST", f"/trace/books/{book_id}/runs",
                task_type=task_type, prompt_version=prompt_version,
                model_name=model_name, params=parsed_params,
                payload={"book_id": book_id}, output_preview="",
                trace_id=trace_id, chapter_ep=ep or None,
            )
            if res:
                st.toast(f"記録しました (hash={res.get('input_hash', '')[:12]}…)", icon="🔬")
                st.rerun()

    st.subheader("📋 記録一覧")
    runs = _get(f"/trace/books/{book_id}/runs") or []
    if not runs:
        st.info("まだ生成実行の記録がありません。")
        return
    for r in runs:
        st.markdown(
            f"- **第{r.get('chapter_ep')}話** `{r.get('task_type')}` | "
            f"モデル: {r.get('model_name')} | プロンプト: {r.get('prompt_version')} | "
            f"hash: `{r.get('input_hash', '')[:12]}…`"
        )

    if st.button("📄 再現性レポートを生成", use_container_width=True):
        report = _get(f"/trace/books/{book_id}/report") or {}
        md = report.get("markdown", "")
        st.markdown(md)
        st.download_button(
            "レポートをMarkdownでダウンロード",
            data=md, file_name="reproducibility_report.md", mime="text/markdown",
        )
