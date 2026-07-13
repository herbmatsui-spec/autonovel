import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.background import BackgroundReporter, ProgressState
from streamlit_app.state import AppStateModel, UIStateStore


@pytest.mark.asyncio
async def test_background_reporter_streaming_persistence():
    # Mock state for UIStateStore
    mock_state = MagicMock(spec=AppStateModel)
    mock_state.active_job = MagicMock()

    with patch('streamlit_app.state.UIStateStore.get', return_value=mock_state):
        # Setup reporter
        # Mock the DB save method to return a future/coroutine to avoid asyncio.create_task TypeError
        mock_db = MagicMock()
        mock_db.save_internal_state = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.db = mock_db

        mock_progress_state = ProgressState(task_id="test_task", repo=mock_repo)
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
