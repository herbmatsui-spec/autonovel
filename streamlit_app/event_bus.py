"""
event_bus.py - UIイベントバス
アプリ内イベントの発行と購読を管理する。
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIEventType(str, Enum):
    """UIイベントの種類"""
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_UPDATED = "job_updated"
    BOOK_CREATED = "book_created"
    BOOK_UPDATED = "book_updated"
    BOOK_DELETED = "book_deleted"


@dataclass
class UIEvent:
    """UIイベントデータ"""
    type: UIEventType
    payload: Any
    timestamp: float = 0.0


UIEventHandler = Callable[[UIEvent], None]


class UIEventBus:
    """UIイベントバス"""

    _instance: Optional["UIEventBus"] = None

    def __init__(self):
        self._subscribers: Dict[UIEventType, List[UIEventHandler]] = {}
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "UIEventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: UIEventType, handler: UIEventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: UIEventType, handler: UIEventHandler) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def publish(self, event: UIEvent) -> None:
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Error in event handler for {event.type}: {e}")
