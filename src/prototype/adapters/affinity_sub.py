"""
src/prototype/adapters/affinity_sub.py - 好感度イベント購読アダプタ
"""

from __future__ import annotations

from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


def register(bus: DomainEventBus, hub: NarrativeState) -> None:
    """AffinityTracker / 好感度イベントを購読し、hub を更新する"""

    def on_written(ev: DomainEvent) -> None:
        text = ev.payload.get("text", "")
        try:
            from src.backend.workflows.adapters.affinity_adapter import update_affinity
            update_affinity(hub, ev.ep, text)
        except Exception:
            pass

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, on_written)
