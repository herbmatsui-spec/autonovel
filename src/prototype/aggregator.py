"""
src/prototype/aggregator.py - ナラティブ評価結果集約モジュール (ステップ 29)
"""

from __future__ import annotations

from typing import Any, Optional
from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


async def aggregate(
    bus: DomainEventBus,
    hub: NarrativeState,
    event: DomainEvent,
) -> DomainEvent:
    """各アダプタによる hub 更新を集約し、EPISODE_EVALUATED イベントを発行する"""
    # 1. もし EPISODE_WRITTEN イベントなら購読者たちへ発行してハブを最新化
    if event.type == NarrativeEventType.EPISODE_WRITTEN:
        await bus.publish(NarrativeEventType.EPISODE_WRITTEN, event)

    # 2. ハブの現在状態を辞書化して EPISODE_EVALUATED イベントを構築
    eval_event = DomainEvent(
        type=NarrativeEventType.EPISODE_EVALUATED,
        payload=hub.to_dict(),
        book_id=event.book_id,
        ep=event.ep,
    )

    # 3. EPISODE_EVALUATED を発行
    await bus.publish(NarrativeEventType.EPISODE_EVALUATED, eval_event)

    return eval_event
