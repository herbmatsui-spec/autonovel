"""
test_commercial_quality_pipeline.py - 商用品質執筆オーケストレーションパイプラインの統合テスト
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec
from src.services.audit_aggregator import AuditAggregator
from src.services.narrative.narrative_spine_composer import NarrativeSpineComposer
from src.services.narrative.opening_booster_service import OpeningBoosterService
from src.services.pdca_cycle import ClosedLoopPDCARunner


@pytest.mark.asyncio
async def test_commercial_quality_pipeline_flow() -> None:
    # 1. Setup narrative spine specs
    hook = EmotionalHookSpec(
        hook_name="despair_to_hope",
        one_line_intent="圧倒的絶望からの逆転",
        target_tension_peak=85,
    )
    edge = SharpEdgeSpec(
        edge_type="cunning",
        description="打算的な生存戦略",
        key_phrase="利益計算は済んでいる",
    )
    composer = NarrativeSpineComposer(hook_spec=hook, edge_spec=edge)
    constraints = composer.compose_constraints()
    assert len(constraints) > 0

    # 2. Opening booster check
    booster = OpeningBoosterService(target_eps=[1])
    tail_peaceful = "今日も平和な一日が終わり、眠りについた。"
    ev = booster.evaluate_tail(1, tail_peaceful)
    assert ev.requires_rewrite is True
    directive = booster.generate_rewrite_directive(ev)
    assert "リライト指令" in directive

    # 3. Closed-loop PDCA runner initialization check
    mock_aggregator = MagicMock(spec=AuditAggregator)
    mock_writer = MagicMock()
    mock_writer.generate_episodes = AsyncMock(return_value=2500)

    runner = ClosedLoopPDCARunner(
        aggregator=mock_aggregator,
        writer=mock_writer,
        target_score=75.0,
        max_cycles=2,
    )
    assert runner.target_score == 75.0
    assert runner.max_cycles == 2
