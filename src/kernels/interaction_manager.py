"""
kernels/interaction_manager.py - インタラクションマネージャー
"""

from typing import Any, Dict, List

from ..shared.event_bus import UIEventType
from .interaction_config import InteractionConfig
from .interaction_formatter import InteractionFormatterFactory


class InteractionManager:
    """
    インタラクション管理
    """

    def __init__(self, config: Optional[InteractionConfig] = None):
        self.config = config or InteractionConfig()
        self.formatter = InteractionFormatterFactory.create_formatter()
        self.events: Dict[str, List[Any]] = {}

    async def send_event(self, event_type: str, data: Any) -> None:
        """イベントを送信"""
        if event_type not in UIEventType:
            return
        if event_type not in self.events:
            self.events[event_type] = []
        self.events[event_type].append(data)

    def register_event_handler(self, event_type: str, handler):
        """イベントハンドラーを登録"""
        if event_type not in self.events:
            self.events[event_type] = []
        self.events[event_type].append(handler)

    async def process_events(self) -> List[Any]:
        """イベントを処理"""
        results = []
        for event_type, handlers in self.events.items():
            for handler in handlers:
                result = await handler()
                results.append(result)
        return results

    def reset_handlers(self) -> None:
        """ハンドラーをリセット"""
        self.events.clear()


# ダミー実装
class DummyHandler:
    async def __call__(self):
        return "processed_event"
