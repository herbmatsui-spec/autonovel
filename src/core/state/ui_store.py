"""
src/core/state/ui_store.py — UI層の状態アクセスをカプセル化するストア
"""
from typing import Any, Callable

import streamlit as st

from schemas.app_state import AppRuntimeState, AppStateModel
from src.core.state.state_manager import SessionManager, get_session


class UIStateStore:
    """
    UI層における状態アクセスをカプセル化するストア。
    st.session_state への直接アクセスを排除し、AppStateModel / AppRuntimeState 経由での
    型安全な操作を強制する。
    """
    _subscribers: dict[str, list[Callable[[Any], None]]] = {}

    @staticmethod
    def get() -> AppStateModel:
        return get_session()

    @staticmethod
    def get_runtime() -> AppRuntimeState:
        """型安全なランタイム状態へのアクセスを提供"""
        return get_session().runtime

    @staticmethod
    def update(update_func: Callable[[AppStateModel], None], notify_keys: list[str] | None = None) -> None:
        """
        状態を安全に更新し、保存する。
        update_func は AppStateModel を受け取り、変更を加える関数であること。
        """
        UIStateStore.increment_rerun_count()
        state = get_session()
        update_func(state)
        SessionManager.save_state(state)

        if notify_keys:
            for key in notify_keys:
                val = getattr(state, key, getattr(state.runtime, key, None))
                UIStateStore._notify(key, val)

    @staticmethod
    def update_runtime(key: str, value: Any, notify: bool = True) -> None:
        """
        ランタイム状態の特定の属性を更新し、状態を保存する。
        """
        state = get_session()
        if hasattr(state.runtime, key):
            setattr(state.runtime, key, value)
        else:
            raise AttributeError(f"AppRuntimeState has no attribute '{key}'")
        SessionManager.save_state(state)
        if notify:
            UIStateStore._notify(key, value)

    @staticmethod
    def persist() -> None:
        """現在の状態をディスクに永続化する"""
        SessionManager.save_state(get_session())

    @staticmethod
    def subscribe(key: str, callback: Callable[[Any], None]) -> None:
        """特定のキーの値が変更されたときに呼び出されるコールバックを登録する"""
        if key not in UIStateStore._subscribers:
            UIStateStore._subscribers[key] = []
        UIStateStore._subscribers[key].append(callback)

    @staticmethod
    def _notify(key: str, value: Any) -> None:
        """登録されたコールバックをすべて実行する"""
        for callback in UIStateStore._subscribers.get(key, []):
            try:
                callback(value)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"State change callback failed for {key}: {e}")

    # ==========================================================================
    # Job Management
    # ==========================================================================
    @staticmethod
    def get_monitored_jobs() -> dict:
        return UIStateStore.get_runtime().monitored_jobs

    @staticmethod
    def set_active_job(job: Any, run_key: str = "default") -> None:
        if job is None:
            UIStateStore.clear_active_job(run_key)
            return

        job_id = getattr(job, "task_id", None)
        UIStateStore.set_job_id(run_key, job_id)

        runtime = UIStateStore.get_runtime()
        current_monitored = runtime.monitored_jobs.copy()
        current_monitored[run_key] = job
        UIStateStore.update_runtime("monitored_jobs", current_monitored)

        UIStateStore._notify(f"active_job_{run_key}", job)

    @staticmethod
    def clear_active_job(run_key: str = "default") -> None:
        UIStateStore.clear_job_id(run_key)

        runtime = UIStateStore.get_runtime()
        if run_key in runtime.monitored_jobs:
            current_monitored = runtime.monitored_jobs.copy()
            current_monitored[run_key] = None
            UIStateStore.update_runtime("monitored_jobs", current_monitored)

        if run_key in runtime.poll_fail_count:
            current_fail = runtime.poll_fail_count.copy()
            current_fail[run_key] = 0
            UIStateStore.update_runtime("poll_fail_count", current_fail)
        if run_key in runtime.poll_skip_until:
            current_skip = runtime.poll_skip_until.copy()
            current_skip[run_key] = 0.0
            UIStateStore.update_runtime("poll_skip_until", current_skip)

        UIStateStore._notify(f"active_job_{run_key}", None)

    @staticmethod
    def set_job_id(run_key: str, job_id: str | None) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.active_job_ids.copy()
        current[run_key] = job_id
        UIStateStore.update_runtime("active_job_ids", current)

    @staticmethod
    def clear_job_id(run_key: str) -> None:
        runtime = UIStateStore.get_runtime()
        if run_key in runtime.active_job_ids:
            current = runtime.active_job_ids.copy()
            current[run_key] = None
            UIStateStore.update_runtime("active_job_ids", current)

    @staticmethod
    def set_processing_lock(locked: bool) -> None:
        UIStateStore.update_runtime("ui_processing_lock", locked)

    @staticmethod
    def is_processing() -> bool:
        return UIStateStore.get_runtime().ui_processing_lock

    # ==========================================================================
    # Polling & Task Progress
    # ==========================================================================
    @staticmethod
    def get_poll_fail_count(run_key: str) -> int:
        return UIStateStore.get_runtime().poll_fail_count.get(run_key, 0)

    @staticmethod
    def increment_poll_fail_count(run_key: str) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.poll_fail_count.copy()
        current[run_key] = current.get(run_key, 0) + 1
        UIStateStore.update_runtime("poll_fail_count", current)

    @staticmethod
    def reset_poll_fail_count(run_key: str) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.poll_fail_count.copy()
        current[run_key] = 0
        UIStateStore.update_runtime("poll_fail_count", current)

    @staticmethod
    def get_poll_skip_until(run_key: str) -> float:
        return UIStateStore.get_runtime().poll_skip_until.get(run_key, 0.0)

    @staticmethod
    def set_poll_skip_until(run_key: str, timestamp: float) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.poll_skip_until.copy()
        current[run_key] = timestamp
        UIStateStore.update_runtime("poll_skip_until", current)

    @staticmethod
    def set_save_status(ep_num: int, status: str) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.save_status.copy()
        current[ep_num] = status
        UIStateStore.update_runtime("save_status", current)
        UIStateStore._notify(f"save_status_{ep_num}", status)

    @staticmethod
    def get_save_status(ep_num: int) -> str:
        return UIStateStore.get_runtime().save_status.get(ep_num, "idle")

    # ==========================================================================
    # Wizard & Genre Settings
    # ==========================================================================
    @staticmethod
    def set_wizard_step(step: int) -> None:
        UIStateStore.update(lambda s: setattr(s.wizard, "step", step), notify_keys=["wizard_step"])

    @staticmethod
    def update_wizard_data(data: dict[str, Any]) -> None:
        UIStateStore.update(lambda s: setattr(s.wizard, "data", data), notify_keys=["wizard_data"])

    @staticmethod
    def set_easy_genre(genre_key: str) -> None:
        UIStateStore.update(lambda s: setattr(s.runtime, "easy_genre_key", genre_key), notify_keys=["easy_genre_key"])

    # ==========================================================================
    # API Key Validation
    # ==========================================================================
    @staticmethod
    def get_api_key_validation_state() -> str:
        return UIStateStore.get_runtime().api_key_validation_state

    @staticmethod
    def set_api_key_validation_state(state: str) -> None:
        UIStateStore.update_runtime("api_key_validation_state", state)

    @staticmethod
    def get_api_key_validation_key() -> str:
        return UIStateStore.get_runtime().api_key_validation_key

    @staticmethod
    def set_api_key_validation_key(key: str) -> None:
        UIStateStore.update_runtime("api_key_validation_key", key)

    @staticmethod
    def get_api_key_validation_error() -> str:
        return UIStateStore.get_runtime().api_key_validation_error

    @staticmethod
    def set_api_key_validation_error(msg: str) -> None:
        UIStateStore.update_runtime("api_key_validation_error", msg)

    @staticmethod
    def reset_api_key_validation() -> None:
        UIStateStore.update(lambda s: (
            setattr(s.runtime, "api_key_validation_state", "idle"),
            setattr(s.runtime, "api_key_validation_error", ""),
        ))

    # ==========================================================================
    # Toast Notification
    # ==========================================================================
    @staticmethod
    def is_toast_notified(key: str) -> bool:
        return key in UIStateStore.get_runtime().toasted_notification_keys

    @staticmethod
    def mark_toast_notified(key: str) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.toasted_notification_keys.copy()
        if key not in current:
            current.append(key)
            UIStateStore.update_runtime("toasted_notification_keys", current)

    @staticmethod
    def clear_toast_notified(key: str) -> None:
        runtime = UIStateStore.get_runtime()
        current = runtime.toasted_notification_keys.copy()
        if key in current:
            current.remove(key)
            UIStateStore.update_runtime("toasted_notification_keys", current)

    @staticmethod
    def toast_notify(key: str, message: str, icon: str = None) -> None:
        if not UIStateStore.is_toast_notified(key):
            st.toast(message, icon=icon)
            UIStateStore.mark_toast_notified(key)

    # ==========================================================================
    # Rerun & Utility
    # ==========================================================================
    @staticmethod
    def get_rerun_count() -> int:
        return UIStateStore.get_runtime().rerun_count

    @staticmethod
    def increment_rerun_count() -> None:
        UIStateStore.update_runtime("rerun_count", UIStateStore.get_runtime().rerun_count + 1)

    @staticmethod
    def get_api_key_input() -> str:
        return UIStateStore.get_runtime().api_key_input

    @staticmethod
    def set_api_key_input(value: str) -> None:
        UIStateStore.update_runtime("api_key_input", value)
