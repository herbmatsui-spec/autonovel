"""
streamlit_app/event_bus.py - UI Event Bus and Event Models
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, Field


class UIEventType(str, Enum):
    REQUEST_GENERATE_PLAN = "REQUEST_GENERATE_PLAN"
    REQUEST_AUDIT_PLAN = "REQUEST_AUDIT_PLAN"
    REQUEST_GENERATE_EPISODE = "REQUEST_GENERATE_EPISODE"
    REQUEST_CANCEL_JOB = "REQUEST_CANCEL_JOB"


class UIEvent(BaseModel):
    type: UIEventType
    payload: Dict[str, Any] = Field(default_factory=dict)


class UIEventHandler(Protocol):
    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]: ...


class UIEventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[UIEventType, List[UIEventHandler]] = {}

    def subscribe(self, event_type: UIEventType, handler: UIEventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def emit(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return None

        last_result: Optional[Dict[str, Any]] = None
        for handler in handlers:
            if hasattr(handler, "handle_event"):
                res = handler.handle_event(event)
            elif callable(handler):
                res = handler(event)
            else:
                res = None
            if res is not None:
                last_result = res
        return last_result
