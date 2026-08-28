"""
tests/unit/test_domain_event_bus.py - ステップ 20, 22: DomainEventBus と NarrativeEventType の単体テスト
"""

import pytest
from src.shared.domain_event_bus import (
    DomainEvent,
    DomainEventBus,
    NarrativeEventType,
    get_domain_event_bus,
)


@pytest.mark.asyncio
async def test_domain_event_bus_subscribe_and_publish():
    """subscribe と publish による非同期ハンドラ実行テスト（ステップ 20）"""
    bus = DomainEventBus()
    received_events = []

    async def sample_handler(ev: DomainEvent):
        received_events.append(ev)

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, sample_handler)

    ev = DomainEvent(
        type=NarrativeEventType.EPISODE_WRITTEN,
        payload={"text": "エピソード本文", "scene": {}},
        book_id=1,
        ep=1,
    )
    await bus.publish(NarrativeEventType.EPISODE_WRITTEN, ev)

    assert len(received_events) == 1
    assert received_events[0].ep == 1
    assert received_events[0].payload["text"] == "エピソード本文"


def test_narrative_event_type_enums():
    """NarrativeEventType 列挙型の値テスト（ステップ 22）"""
    assert NarrativeEventType.EPISODE_WRITTEN == "EPISODE_WRITTEN"
    assert NarrativeEventType.EPISODE_EVALUATED == "EPISODE_EVALUATED"
    assert NarrativeEventType.REVISION_REQUESTED == "REVISION_REQUESTED"


@pytest.mark.asyncio
async def test_domain_event_bus_sync_handler():
    """同期ハンドラも安全に実行できることの検証"""
    bus = DomainEventBus()
    flags = []

    def sync_handler(ev: DomainEvent):
        flags.append(ev.payload.get("status"))

    bus.subscribe("CUSTOM_EVENT", sync_handler)
    await bus.publish("CUSTOM_EVENT", DomainEvent(type="CUSTOM_EVENT", payload={"status": "ok"}))

    assert flags == ["ok"]
