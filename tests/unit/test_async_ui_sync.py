import asyncio
from unittest.mock import MagicMock
import pytest

from src.backend.background import BackgroundReporter, ProgressState
from streamlit_app.state import AppStateModel, UIStateStore


@pytest.mark.asyncio
async def test_background_reporter_streaming_persistence():
    """Test background reporter functionality with mock Streamlit"""
    # Create a ProgressState instance (no streamlit needed for BackgroundReporter)
    progress_state = ProgressState(task_id="test_task", skip_initial_save=True)

    # Setup reporter
    reporter = BackgroundReporter(state=progress_state)

    # Test streaming text update
    test_text = "This is a streaming chunk."
    reporter.update_streaming_text(test_text)

    # Verify state was updated
    assert progress_state.streaming_text == test_text

    # Test progress update
    reporter.update_progress(1, 10, "Step 1", "Doing work")
    assert progress_state.current_step == 1
    assert progress_state.total_steps == 10
    assert "Step 1" in progress_state.message


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
