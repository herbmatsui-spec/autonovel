"""
src/prototype/adapters/continuity_sub.py - 継続性・整合性イベント購読アダプタ
"""

from __future__ import annotations

from typing import Any
from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


def register(bus: DomainEventBus, hub: NarrativeState) -> None:
    """ContinuityTracker / 継続性チェックを購読し、hub を更新する"""

    def on_written(ev: DomainEvent) -> None:
        scene = ev.payload.get("scene", {})
        try:
            from src.backend.workflows.adapters.continuity_adapter import feed_continuity
            feed_continuity(hub, scene)
        except Exception:
            pass

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, on_written)
