"""
src/shared/domain_event_bus.py - ドメインイベントバス（非同期 Pub/Sub）
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class NarrativeEventType(str, Enum):
    """ナラティブ処理におけるドメインイベント種別"""

    EPISODE_WRITTEN = "EPISODE_WRITTEN"
    EPISODE_EVALUATED = "EPISODE_EVALUATED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    BRANCH_FORKED = "BRANCH_FORKED"
    HITL_SUSPENDED = "HITL_SUSPENDED"
    HITL_RESUMED = "HITL_RESUMED"


@dataclass
class DomainEvent:
    """ドメインイベント共通データ構造"""

    type: Union[str, NarrativeEventType]
    payload: Dict[str, Any] = field(default_factory=dict)
    book_id: int = 1
    ep: int = 1


class DomainEventBus:
    """軽量非同期ドメインイベントバス"""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[DomainEvent], Any]]] = {}

    def subscribe(
        self,
        event_type: Union[str, NarrativeEventType],
        handler: Callable[[DomainEvent], Any],
    ) -> None:
        """イベント種別に対するハンドラを登録する"""
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        if key not in self._subs:
            self._subs[key] = []
        self._subs[key].append(handler)

    async def publish(
        self,
        event_type: Union[str, NarrativeEventType],
        event: DomainEvent,
    ) -> None:
        """イベントを発行し、登録された全ハンドラを非同期実行する"""
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        handlers = self._subs.get(key, [])
        for handler in handlers:
            res = handler(event)
            if asyncio.iscoroutine(res):
                await res


# シングルトン / 既定インスタンスの取得
_default_bus: Optional[DomainEventBus] = None


def get_domain_event_bus() -> DomainEventBus:
    """グローバルドメインイベントバスインスタンスを取得"""
    global _default_bus
    if _default_bus is None:
        _default_bus = DomainEventBus()
    return _default_bus
