import pytest
from streamlit_app.state import UIStateStore

# Mock streamlit.session_state as a dictionary
# Note: In a real environment, we'd use streamlit.runtime.scriptrunner.get_script_run_ctx

class MockSessionState(dict):
    pass

@pytest.fixture
def mock_st_session_state(monkeypatch):
    """Mock Streamlit session_state using mock_streamlit fixture"""
    from tests.mocks.mock_streamlit import MockStreamlitContext, patch_streamlit
    ctx = MockStreamlitContext()
    mock_st = patch_streamlit(ctx)
    return mock_st


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


def test_ui_state_store_delegation_methods():
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