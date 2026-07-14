import pytest
import streamlit as st
from streamlit_app.state import UIStateStore
from unittest.mock import MagicMock


class MockSessionState(dict):
    pass


@pytest.fixture
def mock_st_session_state(monkeypatch):
    mock_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", mock_state)
    return mock_state


def test_state_persistence_across_reruns(mock_st_session_state):
    """Streamlit rerun間で状態が保持されることを確認"""
    store1 = UIStateStore()
    initial_count = len(UIStateStore._subscribers)
    
    for i in range(100):
        UIStateStore.subscribe(f"test_key_{i}", lambda x: x)
    
    final_count = len(UIStateStore._subscribers)
    assert final_count == initial_count + 100
    
    UIStateStore._subscribers.clear()


def test_ui_state_store_runtime_access(mock_st_session_state):
    """UIStateStore.get_runtime() がランタイム状態にアクセスできることを確認"""
    store = UIStateStore()
    runtime = store.get_runtime()
    assert runtime is not None
    assert hasattr(runtime, "rerun_count")
    assert hasattr(runtime, "config_data")


def test_subscriber_notification(mock_st_session_state):
    """状態変更時にサブスクライバーが通知されることを確認"""
    store = UIStateStore()
    callback_calls = []
    
    def test_callback(value):
        callback_calls.append(value)
    
    UIStateStore.subscribe("rerun_count", test_callback)
    UIStateStore.update_runtime("rerun_count", 999, notify=True)
    
    assert len(callback_calls) == 1
    assert callback_calls[0] == 999
    
    UIStateStore._subscribers.clear()
