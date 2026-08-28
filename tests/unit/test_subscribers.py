"""
tests/unit/test_subscribers.py - ステップ 28: 各ドメインイベント購読アダプタの単体テスト
"""

import pytest
from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType
from src.prototype.adapters import (
    tension_sub,
    affinity_sub,
    continuity_sub,
    narrative_sub,
    erotic_sub,
)


@pytest.mark.asyncio
async def test_all_subscribers_on_written():
    """EPISODE_WRITTEN 発行で全購読者が動作し NarrativeState ハブが更新されることを検証"""
    bus = DomainEventBus()
    hub = NarrativeState()

    # 全購読者を登録
    tension_sub.register(bus, hub)
    affinity_sub.register(bus, hub)
    continuity_sub.register(bus, hub)
    narrative_sub.register(bus, hub)
    erotic_sub.register(bus, hub)

    # イベント発行
    sample_text = "凛はセリアと共に光の石の回廊を歩いた。セリアは微笑みかけた。二人の距離が近づく。"
    sample_scene = {
        "id": "scene_01",
        "type": "combat",
        "hp": 90,
        "mp": 40,
    }

    event = DomainEvent(
        type=NarrativeEventType.EPISODE_WRITTEN,
        payload={
            "text": sample_text,
            "scene": sample_scene,
            "tension": 0.85,
        },
        book_id=1,
        ep=1,
    )

    await bus.publish(NarrativeEventType.EPISODE_WRITTEN, event)

    # hub の状態を検証
    assert 1 in hub.episodes
    assert hub.episodes[1]["tension"] == 0.85
    assert len(hub.tension_curve) >= 1
