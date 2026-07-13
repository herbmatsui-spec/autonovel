import pytest
import streamlit as st
from streamlit_app.state import UIStateStore, UIState
from unittest.mock import MagicMock

# Mock streamlit.session_state as a dictionary
# Note: In a real environment, we'd use streamlit.runtime.scriptrunner.get_script_run_ctx
# but for unit testing the logic, we can mock the session_state.

class MockSessionState(dict):
    pass

@pytest.fixture
def mock_st_session_state(monkeypatch):
    mock_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", mock_state)
    return mock_state

def test_ui_state_initialization(mock_st_session_state):
    """UIStateStore.ui_state が正しく初期化されるかテスト"""
    store = UIStateStore()
    state = store.ui_state
    
    assert isinstance(state, UIState)
    assert state.active_tab == "home"
    from streamlit_app.state_keys import UI_STATE_KEY
    assert UI_STATE_KEY in mock_st_session_state

def test_update_ui_state_explicit_field(mock_st_session_state):
    """UIStateStore.update_ui_state が明示的なフィールドを更新できるかテスト"""
    store = UIStateStore()
    store.update_ui_state(active_tab="analytics")
    
    assert store.ui_state.active_tab == "analytics"

def test_update_ui_state_dynamic_field(mock_st_session_state):
    """UIStateStore.update_ui_state が動的なデータを form_data に格納するかテスト"""
    store = UIStateStore()
    store.update_ui_state(custom_setting="enabled")
    
    assert store.ui_state.form_data.get("custom_setting") == "enabled"

def test_ui_state_persistence_in_session(mock_st_session_state):
    """UIState が st.session_state に保持され、再取得時に維持されるかテスト"""
    store1 = UIStateStore()
    store1.update_ui_state(active_tab="writing")
    
    # 新しいストアインスタンスを作成しても状態が維持されているか
    store2 = UIStateStore()
    assert store2.ui_state.active_tab == "writing"
