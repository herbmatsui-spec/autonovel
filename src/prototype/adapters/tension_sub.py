"""
src/prototype/adapters/tension_sub.py - テンション曲線イベント購読アダプタ
"""

from __future__ import annotations

from typing import Any
from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


def register(bus: DomainEventBus, hub: NarrativeState) -> None:
    """TensionService / テンションイベントを購読し、hub を更新する"""

    async def on_written(ev: DomainEvent) -> None:
        tension_val = ev.payload.get("tension", 0.5)
        try:
            from src.backend.workflows.adapters.tension_adapter import update_tension
            await update_tension(hub, ev.ep, tension_val)
        except Exception:
            hub.upsert_episode(ev.ep, tension=tension_val)

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, on_written)
