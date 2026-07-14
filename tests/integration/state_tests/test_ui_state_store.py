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

def test_get_ui_state_value_explicit_field(mock_st_session_state):
    """get_ui_state_value が明示的なフィールドを取得できるかテスト"""
    store = UIStateStore()
    store.update_ui_state(active_tab="plots")
    assert store.get_ui_state_value("active_tab") == "plots"

def test_get_ui_state_value_default(mock_st_session_state):
    """get_ui_state_value が存在しないキーにデフォルト値を返すかテスト"""
    store = UIStateStore()
    assert store.get_ui_state_value("non_existent_key", "default") == "default"

def test_reset_ui_state(mock_st_session_state):
    """reset_ui_state が状態をデフォルトにリセットするかテスト"""
    store = UIStateStore()
    store.update_ui_state(active_tab="analytics", show_modal=True)
    store.reset_ui_state()
    
    state = store.ui_state
    assert state.active_tab == "home"
    assert state.show_modal is False

def test_set_and_get_form_data(mock_st_session_state):
    """set_form_data / get_form_data がフォームデータを管理するかテスト"""
    store = UIStateStore()
    store.set_form_data("username", "test_user")
    store.set_form_data("preferences", {"theme": "dark"})
    
    assert store.get_form_data("username") == "test_user"
    assert store.get_form_data("preferences") == {"theme": "dark"}
    assert store.get_form_data("missing_key", "fallback") == "fallback"

def test_set_modal_visible(mock_st_session_state):
    """set_modal_visible / is_modal_visible がモーダル状態を管理するかテスト"""
    store = UIStateStore()
    assert store.is_modal_visible() is False
    
    store.set_modal_visible(True)
    assert store.is_modal_visible() is True
    
    store.set_modal_visible(False)
    assert store.is_modal_visible() is False
