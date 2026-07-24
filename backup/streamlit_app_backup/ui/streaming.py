from __future__ import annotations

import typing
from typing import Any, List, Optional

import streamlit as st

from streamlit_app.ui.ui_types import StreamDisplayInterface

T = typing.TypeVar("T")


class StreamlitStreamDisplay(StreamDisplayInterface):
    """
    Streamlit向けの実装。
    st.empty() を利用してリアルタイムにUIを更新する（状態管理はUIStateStore経由）。
    """

    def __init__(self, run_key: str):
        self.run_key = run_key
        self.status_container = st.empty()
        self.log_container = st.expander("🔍 リアルタイム・ログ", expanded=True)
        self.text_container = st.empty()
        self._logs: List[str] = []

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        pct = min(1.0, current / total) if total > 0 else 0.0
        with self.status_container.container(border=True):
            st.markdown(f"### ⚙️ {message}")
            st.progress(pct, text=f"全体進捗: {current}/{total} ({int(pct * 100)}%)")

    def append_log(self, message: str) -> None:
        self._logs.append(message)
        with self.log_container:
            # 直近5件のみ表示してパフォーマンスを維持
            for log in self._logs[-5:]:
                st.caption(log)

    def update_text(self, text: str, finalize: bool = False) -> None:
        self.text_container.markdown(text)
        if finalize:
            self.text_container.success("✅ 生成が完了しました。")

    def set_error(self, error_message: str, trace_id: Optional[str] = None) -> None:
        with self.status_container.container(border=True):
            st.error(f"🚨 エラーにより停止: {error_message}")
            if trace_id:
                st.code(f"TraceID: {trace_id}")
        st.toast("🚨 タスクの実行中にエラーが発生しました。", icon="🚨")

    def set_complete(self, result_data: Any = None, message: str = "") -> None:
        with self.status_container.container(border=True):
            st.success(f"✨ 完了！ {message}")
            if result_data:
                st.write(result_data)
        st.toast("✨ タスクが正常に完了しました！", icon="✨")
