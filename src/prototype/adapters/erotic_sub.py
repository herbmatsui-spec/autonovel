"""
src/prototype/adapters/erotic_sub.py - 官能品質スコア購読アダプタ
"""

from __future__ import annotations

from src.backend.workflows.narrative_state import NarrativeState
from src.shared.domain_event_bus import DomainEvent, DomainEventBus, NarrativeEventType


def register(bus: DomainEventBus, hub: NarrativeState) -> None:
    """EroticQualityScorer / 官能品質スコアを購読し、hub を更新する"""

    def on_written(ev: DomainEvent) -> None:
        text = ev.payload.get("text", "")
        try:
            from src.backend.workflows.adapters.erotic_adapter import update_erotic
            update_erotic(hub, ev.ep, text)
        except Exception:
            pass

    bus.subscribe(NarrativeEventType.EPISODE_WRITTEN, on_written)
