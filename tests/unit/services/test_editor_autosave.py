import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.writing_langgraph import WritingGraphManager

@pytest.mark.asyncio
async def test_writing_manager_saves_checkpoint():
    # Mock the manager (GenerationLoopManager)
    mock_manager = MagicMock()
    mock_manager.session_factory = AsyncMock()

    # Create WritingGraphManager instance
    wgm = WritingGraphManager(mock_manager)

    # Replace the checkpoint_manager with a mock
    mock_checkpoint_manager = MagicMock()
    wgm.checkpoint_manager = mock_checkpoint_manager

    # Prepare a state dict
    state = {
        "task_id": "task_123",
        "ep_num": 5,
        "draft_content": "Once upon a time...",
        "audit_result": {"is_integrity_ok": True},
        "ac_iter": 2
    }

    # Call the internal method
    wgm._save_checkpoint_if_needed(state, "drafting", 1)

    # Verify that checkpoint_manager.record_step was called
    mock_checkpoint_manager.record_step.assert_called_once()
    # Check the arguments
    call_args = mock_checkpoint_manager.record_step.call_args
    assert call_args is not None
    kwargs = call_args.kwargs
    assert kwargs["task_id"] == "task_123"
    assert kwargs["step_name"] == "drafting"
    assert kwargs["step_index"] == 1
    assert kwargs["status"] == "completed"  # CheckpointStatus.COMPLETED
    # Check that state_payload contains expected keys
    assert "ep_num" in kwargs["state_payload"]
    assert kwargs["state_payload"]["ep_num"] == 5
    assert "draft" in kwargs["state_payload"]
    assert kwargs["state_payload"]["draft"] == "Once upon a time..."
    assert "audit_result" in kwargs["state_payload"]
    assert kwargs["state_payload"]["audit_result"]["is_integrity_ok"] is True
    assert "ac_iter" in kwargs["state_payload"]
    assert kwargs["state_payload"]["ac_iter"] == 2
