"""
streamlit_app/stores/toast_store.py — Toast通知の重複防止状態管理。

責務:
- 通知済みキー(toasted_notification_keys)の確認・マーク・クリア
- 重複を制御した toast 通知(toast_notify)
"""
from __future__ import annotations

import streamlit as st

from streamlit_app.state import SessionManager, get_session
from streamlit_app.stores.base import BaseStore


class ToastStore(BaseStore):
    """Toast通知の状態アクセスをカプセル化するストア。"""

    @staticmethod
    def is_toast_notified(key: str) -> bool:
        """指定キーの toast が既に表示済みか"""
        return key in ToastStore.get_runtime().toasted_notification_keys

    @staticmethod
    def mark_toast_notified(key: str) -> None:
        """指定キーの toast を表示済みとしてマーク"""
        runtime = ToastStore.get_runtime()
        current = runtime.toasted_notification_keys.copy()
        if key not in current:
            current.append(key)
            ToastStore.update_runtime("toasted_notification_keys", current, notify=False)
            SessionManager.save_state(get_session())  # 明示的に保存

    @staticmethod
    def clear_toast_notified(key: str) -> None:
        """指定キーの toast 表示済みマークをクリア"""
        runtime = ToastStore.get_runtime()
        current = runtime.toasted_notification_keys.copy()
        if key in current:
            current.remove(key)
            ToastStore.update_runtime("toasted_notification_keys", current)

    @staticmethod
    def toast_notify(key: str, message: str, icon: str = None) -> None:
        """重複して通知が出ないように制御された toast 通知を行う"""
        if not ToastStore.is_toast_notified(key):
            st.toast(message, icon=icon)
            ToastStore.mark_toast_notified(key)
