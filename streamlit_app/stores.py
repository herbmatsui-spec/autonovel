"""
streamlit_app/stores.py - Modular UI state stores
"""
from typing import Any, Callable, Dict, List, Optional
import streamlit as st


class BaseStore:
    _subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    @classmethod
    def get(cls) -> Any:
        from streamlit_app.state import SessionManager
        return SessionManager.get_state()

    @classmethod
    def get_runtime(cls) -> Any:
        class MockRuntime:
            rerun_count = 0
            config_data = {}
        if "runtime_state" not in st.session_state:
            st.session_state["runtime_state"] = MockRuntime()
        return st.session_state["runtime_state"]

    @classmethod
    def update(cls, update_func: Callable[[Any], None], notify_keys: Optional[List[str]] = None) -> None:
        state = cls.get()
        update_func(state)
        if notify_keys:
            for k in notify_keys:
                val = getattr(state, k, None)
                cls._notify(k, val)

    @classmethod
    def update_runtime(cls, key: str, value: Any, notify: bool = True) -> None:
        runtime = cls.get_runtime()
        setattr(runtime, key, value)
        if notify:
            cls._notify(key, value)

    @classmethod
    def subscribe(cls, key: str, callback: Callable[[Any], None]) -> Callable[[], None]:
        if key not in cls._subscribers:
            cls._subscribers[key] = []
        cls._subscribers[key].append(callback)

        def unsubscribe():
            if key in cls._subscribers and callback in cls._subscribers[key]:
                cls._subscribers[key].remove(callback)
        return unsubscribe

    @classmethod
    def _notify(cls, key: str, value: Any) -> None:
        if key in cls._subscribers:
            for cb in list(cls._subscribers[key]):
                try:
                    cb(value)
                except Exception:
                    pass

    @classmethod
    def get_rerun_count(cls) -> int:
        return getattr(cls.get_runtime(), "rerun_count", 0)

    @classmethod
    def increment_rerun_count(cls) -> int:
        rt = cls.get_runtime()
        count = getattr(rt, "rerun_count", 0) + 1
        setattr(rt, "rerun_count", count)
        return count

    @classmethod
    def get_book_plots(cls, book_id: Any) -> List[Any]:
        return []


class JobStore(BaseStore):
    @classmethod
    def get_monitored_jobs(cls) -> Dict[str, Any]:
        return st.session_state.get("monitored_jobs", {})

    @classmethod
    def set_active_job(cls, job: Any, run_key: str = "default") -> None:
        if "monitored_jobs" not in st.session_state:
            st.session_state["monitored_jobs"] = {}
        st.session_state["monitored_jobs"][run_key] = job

    @classmethod
    def clear_active_job(cls, run_key: str = "default") -> None:
        if "monitored_jobs" in st.session_state and run_key in st.session_state["monitored_jobs"]:
            del st.session_state["monitored_jobs"][run_key]

    @classmethod
    def bump_fragment_version(cls, part: str) -> int:
        key = f"frag_ver_{part}"
        val = st.session_state.get(key, 0) + 1
        st.session_state[key] = val
        return val

    @classmethod
    def get_fragment_version(cls, part: str) -> int:
        return st.session_state.get(f"frag_ver_{part}", 0)

    @classmethod
    def set_job_id(cls, run_key: str, job_id: str) -> None:
        st.session_state[f"job_id_{run_key}"] = job_id

    @classmethod
    def clear_job_id(cls, run_key: str) -> None:
        key = f"job_id_{run_key}"
        if key in st.session_state:
            del st.session_state[key]

    @classmethod
    def set_processing_lock(cls, locked: bool) -> None:
        st.session_state["processing_lock"] = locked

    @classmethod
    def is_processing(cls) -> bool:
        return st.session_state.get("processing_lock", False)


class PollStateStore(BaseStore):
    @classmethod
    def get_poll_fail_count(cls, run_key: str) -> int:
        return st.session_state.get(f"poll_fail_{run_key}", 0)

    @classmethod
    def increment_poll_fail_count(cls, run_key: str) -> int:
        val = cls.get_poll_fail_count(run_key) + 1
        st.session_state[f"poll_fail_{run_key}"] = val
        return val

    @classmethod
    def reset_poll_fail_count(cls, run_key: str) -> None:
        st.session_state[f"poll_fail_{run_key}"] = 0

    @classmethod
    def get_poll_skip_until(cls, run_key: str) -> float:
        return st.session_state.get(f"poll_skip_{run_key}", 0.0)

    @classmethod
    def set_poll_skip_until(cls, run_key: str, timestamp: float) -> None:
        st.session_state[f"poll_skip_{run_key}"] = timestamp

    @classmethod
    def set_save_status(cls, ep_num: int, status: str) -> None:
        st.session_state[f"save_status_{ep_num}"] = status

    @classmethod
    def get_save_status(cls, ep_num: int) -> str:
        return st.session_state.get(f"save_status_{ep_num}", "idle")


class ToastStore(BaseStore):
    @classmethod
    def is_toast_notified(cls, key: str) -> bool:
        return key in st.session_state.get("notified_toasts", set())

    @classmethod
    def mark_toast_notified(cls, key: str) -> None:
        if "notified_toasts" not in st.session_state:
            st.session_state["notified_toasts"] = set()
        st.session_state["notified_toasts"].add(key)

    @classmethod
    def clear_toast_notified(cls, key: str) -> None:
        if "notified_toasts" in st.session_state and key in st.session_state["notified_toasts"]:
            st.session_state["notified_toasts"].remove(key)

    @classmethod
    def toast_notify(cls, key: str, message: str, icon: Optional[str] = None) -> None:
        cls.mark_toast_notified(key)
        if hasattr(st, "toast"):
            st.toast(message, icon=icon)


class SessionStore(BaseStore):
    @classmethod
    def set_wizard_step(cls, step: int) -> None:
        cls.update(lambda s: setattr(s.wizard, "step", step) if hasattr(s, "wizard") else None)

    @classmethod
    def update_wizard_data(cls, data: Dict[str, Any]) -> None:
        cls.update(lambda s: s.wizard.data.update(data) if hasattr(s, "wizard") else None)

    @classmethod
    def set_easy_genre(cls, genre_key: str) -> None:
        st.session_state["easy_genre"] = genre_key

    @classmethod
    def get_api_key_validation_state(cls) -> str:
        return st.session_state.get("api_key_validation_state", "unvalidated")

    @classmethod
    def set_api_key_validation_state(cls, state: str) -> None:
        st.session_state["api_key_validation_state"] = state

    @classmethod
    def get_api_key_validation_key(cls) -> str:
        return st.session_state.get("api_key_validation_key", "")

    @classmethod
    def set_api_key_validation_key(cls, key: str) -> None:
        st.session_state["api_key_validation_key"] = key

    @classmethod
    def get_api_key_validation_error(cls) -> str:
        return st.session_state.get("api_key_validation_error", "")

    @classmethod
    def set_api_key_validation_error(cls, msg: str) -> None:
        st.session_state["api_key_validation_error"] = msg

    @classmethod
    def reset_api_key_validation(cls) -> None:
        st.session_state["api_key_validation_state"] = "unvalidated"
        st.session_state["api_key_validation_key"] = ""
        st.session_state["api_key_validation_error"] = ""

    @classmethod
    def get_api_key_input(cls) -> str:
        return st.session_state.get("api_key_input", "")

    @classmethod
    def set_api_key_input(cls, value: str) -> None:
        st.session_state["api_key_input"] = value
