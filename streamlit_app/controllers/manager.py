"""
streamlit_app/controllers/manager.py - UI Controller Manager
"""

from typing import Any, Dict, Optional

from streamlit_app.event_bus import UIEvent, UIEventBus, UIEventType


class SubController:
    def __init__(self, engine: Any):
        self.engine = engine
        self.stream_display: Optional[Any] = None

    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        return {"status": "ok"}


class UIControllerManager:
    def __init__(self, engine: Any):
        self.engine = engine
        self.bus = UIEventBus()
        self.planning_ctrl = SubController(engine)
        self.writing_ctrl = SubController(engine)
        self.system_ctrl = SubController(engine)

        # デフォルトでハンドラ登録
        self.bus.subscribe(UIEventType.REQUEST_GENERATE_PLAN, self.planning_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_AUDIT_PLAN, self.planning_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_GENERATE_EPISODE, self.writing_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_CANCEL_JOB, self.system_ctrl)

    def emit(
        self, event_type: UIEventType, payload: Dict[str, Any], stream_display: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        if stream_display is not None:
            self.planning_ctrl.stream_display = stream_display
            self.writing_ctrl.stream_display = stream_display
            self.system_ctrl.stream_display = stream_display

        event = UIEvent(type=event_type, payload=payload)
        return self.bus.emit(event)
