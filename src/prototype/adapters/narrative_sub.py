"""
src/prototype/adapters/narrative_sub.py - ナラティブ品質スコア購読アダプタ
"""

from __future__ import annotations

from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


def register(bus: DomainEventBus, hub: NarrativeState) -> None:
    """NarrativeScoringService / ナラティブ品質スコアリングを購読し、hub を更新する"""

    async def on_written(ev: DomainEvent) -> None:
        text = ev.payload.get("text", "")
        try:
            from src.backend.workflows.adapters.narrative_adapter import update_narrative
            await update_narrative(hub, ev.ep, text)
        except Exception:
            pass

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, on_written)
