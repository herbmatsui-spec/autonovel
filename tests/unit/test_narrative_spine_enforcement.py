"""
test_narrative_spine_enforcement.py - EmotionalHookSpec と SharpEdgeSpec のプロンプト注入・制約保全テスト
"""
from __future__ import annotations

import pytest

from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec
from src.services.narrative.narrative_spine_composer import NarrativeSpineComposer


def test_narrative_spine_composer() -> None:
    hook = EmotionalHookSpec(
        hook_name="despair_to_hope",
        one_line_intent="絶望からの一筋の光",
        target_tension_peak=90,
        subordinate_to_quality=True,
    )
    edge = SharpEdgeSpec(
        edge_type="madness",
        description="主人公の狂気的な執着",
        key_phrase="絶対に許さない",
        preserve_on_quality_polish=True,
    )
    composer = NarrativeSpineComposer(hook_spec=hook, edge_spec=edge)
    constraints = composer.compose_constraints()

    assert "despair_to_hope" in constraints
    assert "絶望からの一筋の光" in constraints
    assert "madness" in constraints
    assert "絶対に許さない" in constraints
