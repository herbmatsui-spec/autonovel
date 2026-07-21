import pytest
from streamlit_app.state import UIStateStore
from streamlit_app.stores.base import BaseStore
from streamlit_app.stores.job_store import JobStore
from streamlit_app.stores.poll_store import PollStateStore
from streamlit_app.stores.session_store import SessionStore
from streamlit_app.stores.toast_store import ToastStore

def test_ui_state_store_delegation():
    """UIStateStoreに必要なDelegationメソッドが存在することを確認するテスト"""
    methods_to_check = [
        "get_runtime",
        "get_runtime_state",
        "get_monitored_jobs",
        "set_active_job",
        "clear_active_job",
        "get_poll_fail_count",
        "increment_poll_fail_count",
        "reset_poll_fail_count",
        "get_api_key_input",
        "set_api_key_input",
        "get_rerun_count",
        "increment_rerun_count",
    ]
    for method in methods_to_check:
        assert hasattr(UIStateStore, method), f"UIStateStore is missing static method: {method}"
