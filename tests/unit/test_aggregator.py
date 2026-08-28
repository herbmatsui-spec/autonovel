"""
tests/unit/test_aggregator.py - ステップ 30: aggregator の単体テスト
"""

import pytest
from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType
from src.prototype.adapters import tension_sub
from src.prototype.aggregator import aggregate


@pytest.mark.asyncio
async def test_aggregator_publishes_evaluated():
    """aggregator 呼び出しで EPISODE_EVALUATED が発行されハンドラが受け取ることを検証"""
    bus = DomainEventBus()
    hub = NarrativeState()

    # 購読者登録
    tension_sub.register(bus, hub)

    evaluated_events = []

    async def on_evaluated(ev: DomainEvent):
        evaluated_events.append(ev)

    bus.subscribe(NarrativeEventType.EPISODE_EVALUATED, on_evaluated)

    # written イベント
    written_ev = DomainEvent(
        type=NarrativeEventType.EPISODE_WRITTEN,
        payload={"text": "本文", "tension": 0.9},
        book_id=1,
        ep=1,
    )

    out_event = await aggregate(bus, hub, written_ev)

    assert out_event.type == NarrativeEventType.EPISODE_EVALUATED
    assert len(evaluated_events) == 1
    assert evaluated_events[0].ep == 1
    assert "tension_curve" in evaluated_events[0].payload
    assert evaluated_events[0].payload["episodes"][1]["tension"] == 0.9
