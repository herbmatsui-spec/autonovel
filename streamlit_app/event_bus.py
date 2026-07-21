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

    # コントローラーリクエストイベント
    REQUEST_GENERATE_PLAN = "request_generate_plan"
    REQUEST_AUDIT_PLAN = "request_audit_plan"
    REQUEST_EXPAND_PLOT = "request_expand_plot"
    REQUEST_WRITE_EPISODE = "request_write_episode"
    REQUEST_IMPORT_CHAPTER = "request_import_chapter"
    REQUEST_DELETE_CHAPTER = "request_delete_chapter"
    REQUEST_DELETE_BOOK = "request_delete_book"
    REQUEST_REBUILD_PLOT = "request_rebuild_plot"


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

    def publish(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        handlers = self._subscribers.get(event.type, [])
        result = None
        for handler in handlers:
            try:
                if hasattr(handler, "handle_event"):
                    result = handler.handle_event(event)
                else:
                    result = handler(event)
            except Exception as e:
                logger.warning(f"Error in event handler for {event.type}: {e}")
        return result

    def emit(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        """publish のエイリアス"""
        return self.publish(event)
