import asyncio
import pytest
from src.backend.background import BackgroundReporter, ProgressState
from streamlit_app.state import AppStateModel, UIStateStore


@pytest.mark.asyncio
async def test_background_reporter_streaming_persistence():
    """Mock Streamlit session state for testing background reporter functionality"""
    # Mock Streamlit session state using mock_streamlit fixture
    from tests.mocks.mock_streamlit import mock_st_context
    mock_st = mock_st_context()
    
    # Mock state for UIStateStore
    mock_state = MagicMock(spec=AppStateModel)
    mock_state.active_job = MagicMock()
    
    # Set up the mock state
    mock_state.active_job = MagicMock()
    
    # Set up the background reporter
    async with mock_st:  # This will patch streamlit appropriately
        # Setup reporter
        reporter = BackgroundReporter(state=mock_progress_state)
        
        # Test streaming text update
        test_text = "This is a streaming chunk."
        reporter.update_streaming_text(test_text)
        
        # Verify state was updated
        assert mock_progress_state.streaming_text == test_text
        
        # Verify that persistence was triggered via the repo's save method
        mock_db.save_internal_state.assert_called()


@pytest.mark.asyncio
async def test_async_ui_state_sync_consistency():
    """UI state consistency check with mock streamlit context"""
    from tests.mocks.mock_streamlit import mock_st_context
    
    # Set up the mock context
    mock_st = mock_st_context()
    
    # Simulate a race condition: UI update vs Async background update
    # 1. Initial state
    UIStateStore.update(lambda s: setattr(s.wizard, "step", 1))
    
    # 2. Concurrent updates
    async def ui_update():
        UIStateStore.set_wizard_step(2)
    
    async def bg_update():
        # Simulate background worker updating some data
        UIStateStore.update(lambda s: setattr(s.wizard, "data", {"status": "done"}))
    
    await asyncio.gather(ui_update(), bg_update())
    
    # 3. Verify consistency
    state = UIStateStore.get()
    assert state.wizard.step == 2
    assert state.wizard.data["status"] == "done"