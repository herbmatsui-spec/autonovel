"""
ui_tabs_cost.py - 執筆コスト・トークン最適化ダッシュボードのStreamlit UI
"""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def _fetch_summary(book_id: int) -> Dict[str, Any]:
    try:
        from streamlit_app.api_client import _request

        return _request("GET", f"/cost/books/{book_id}/summary") or {}
    except Exception as exc:  # noqa: BLE001
        st.error(f"コスト集計の取得に失敗しました: {exc}")
        return {}


def _post_record(book_id: int, task_type: str, inp: int, out: int, ep: int | None = None) -> None:
    try:
        from streamlit_app.api_client import _request

        _request(
            "POST",
            f"/cost/books/{book_id}/records",
            task_type=task_type,
            input_tokens=inp,
            output_tokens=out,
            ep_num=ep,
        )
        st.toast("コストを記録しました", icon="💰")
    except Exception as exc:  # noqa: BLE001
        st.error(f"記録に失敗しました: {exc}")


def _set_budget(book_id: int, budget: float) -> None:
    try:
        from streamlit_app.api_client import _request

        _request("POST", f"/cost/books/{book_id}/budget", budget_usd=budget)
        st.toast("予算を設定しました", icon="✔")
    except Exception as exc:  # noqa: BLE001
        st.error(f"予算設定に失敗しました: {exc}")


def render_cost_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_COST

    st.header(f"{ICON_COST} 執筆コスト・トークン分析")
    st.write(
        "各生成処理のトークン使用量と推定コスト（USD）を可視化します。"
        "予算を設定すると超過を警告し、無駄な生成を抑えるための目安になります。"
    )

    summary = _fetch_summary(book_id)
    if not summary:
        st.info("コスト記録がありません。下のフォームから手動記録できます。")

    total_tokens = summary.get("total_tokens", 0)
    total_cost = summary.get("total_cost_usd", 0.0)
    c1, c2, c3 = st.columns(3)
    c1.metric("総トークン", f"{total_tokens:,}")
    c2.metric("推定コスト", f"${total_cost:.4f}")
    c3.metric("記録数", summary.get("record_count", 0))

    # 予算設定
    with st.form("budget_form", border=True):
        st.subheader("予算設定")
        budget = st.number_input("予算 (USD)", min_value=0.0, value=1.0, step=0.1)
        if st.form_submit_button("予算を保存"):
            _set_budget(book_id, budget)
            st.rerun()

    # タスク別内訳
    by_task = summary.get("by_task", {})
    if by_task:
        st.subheader("タスク別内訳")
        for task, info in by_task.items():
            st.markdown(f"- **{task}**: {info['tokens']:,} tokens / ${info['cost']:.4f} / {info['calls']}回")

    # 手動記録
    with st.form("manual_cost", border=True):
        st.subheader("手動コスト記録")
        task_type = st.selectbox("タスク種別", ["writing", "planning", "plot_expansion", "audit", "marketing"])
        col_i, col_o = st.columns(2)
        inp = col_i.number_input("入力トークン", min_value=0, value=0, step=100)
        out = col_o.number_input("出力トークン", min_value=0, value=0, step=100)
        ep = st.number_input("エピソード番号（任意）", min_value=0, value=0, step=1)
        if st.form_submit_button("記録"):
            _post_record(book_id, task_type, inp, out, ep or None)
            st.rerun()
