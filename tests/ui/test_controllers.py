from unittest.mock import MagicMock

from streamlit_app.controllers.manager import UIControllerManager
from streamlit_app.event_bus import UIEventType


def test_ui_controller_manager_emit():
    # Mock the engine
    mock_engine = MagicMock()

    # Initialize manager
    manager = UIControllerManager(mock_engine)

    # Mock the specific controller's handle_event method
    # Since PlanningController is a real class, we can mock its handle_event
    manager.planning_ctrl.handle_event = MagicMock(return_value={"status": "ok"})

    payload = {"genre": "test"}
    result = manager.emit(UIEventType.REQUEST_GENERATE_PLAN, payload)

    assert result == {"status": "ok"}
    manager.planning_ctrl.handle_event.assert_called_once()
    # Verify the event object was created correctly
    event = manager.planning_ctrl.handle_event.call_args[0][0]
    assert event.type == UIEventType.REQUEST_GENERATE_PLAN
    assert event.payload == payload

def test_ui_controller_manager_stream_injection():
    mock_engine = MagicMock()
    manager = UIControllerManager(mock_engine)
    mock_display = MagicMock()

    # Emit with stream_display
    manager.emit(UIEventType.REQUEST_GENERATE_PLAN, {}, stream_display=mock_display)

    # Check if stream_display was injected into controllers
    assert manager.planning_ctrl.stream_display == mock_display
    assert manager.writing_ctrl.stream_display == mock_display
    assert manager.system_ctrl.stream_display == mock_display
