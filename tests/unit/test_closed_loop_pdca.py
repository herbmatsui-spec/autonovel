"""Unit and integration tests for Closed-Loop PDCA Runner (Part 4 / Step 48 / Checkpoint 8)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult, ActionableDiff
from src.services.audit_aggregator import AuditAggregator, SPECIALIST_NAMES
from src.services.pdca_cycle import ClosedLoopPDCARunner


def create_mock_specialist(name: str, score_sequence: list[float]) -> SpecialistAuditor:
    s = MagicMock(spec=SpecialistAuditor)
    s.specialist_name = name
    call_idx = [0]

    async def _safe_audit(ctx):
        idx = min(call_idx[0], len(score_sequence) - 1)
        score = score_sequence[idx]
        call_idx[0] += 1
        diff = ActionableDiff(
            location=f"{name} 箇所",
            original_quote="問題のある文",
            improved_suggestion="改善提案文",
            rationale="弱点克服",
        )
        return SpecialistAuditResult(
            specialist_name=name,
            score=score,
            confidence=0.9,
            actionable_diffs=[diff],
        )

    s._safe_audit = _safe_audit
    return s


@pytest.mark.asyncio
async def test_pdca_cycle_convergence_and_improvement():
    """Verify PDCA runner iterates, applies directives, and achieves >= 15% score improvement."""
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    # Initial audit: 60.0 (all specialists)
    # Cycle 1 rewrite: 70.0
    # Cycle 2 rewrite: 78.0 (exceeds target_score 75.0 -> converges)
    specialists = [
        create_mock_specialist(n, [60.0, 70.0, 78.0])
        for n in SPECIALIST_NAMES
    ]
    agg = AuditAggregator(specialists=specialists, weights=eq_w)

    async def mock_writer(ctx):
        cycle = ctx.get("pdca_cycle", 1)
        directives = ctx.get("pdca_directives", "")
        assert "閉ループPDCA" in directives
        return f"改訂版ドラフト（サイクル{cycle}）：ディレクティブを反映して文章を大幅改善しました。"

    runner = ClosedLoopPDCARunner(
        aggregator=agg,
        writer=mock_writer,
        target_score=75.0,
        max_cycles=3,
        min_improvement_delta=1.0,
    )

    ctx = {"draft_text": "初稿ドラフト。事件も山場もない平坦な文章。"}
    best_draft, result = await runner.run_pdca_cycle(ctx, genre="general")

    assert result.converged is True
    assert result.cycle_number == 2
    assert result.initial_score < 65.0
    assert result.final_score >= 75.0
    assert result.score_delta > 0
    # 改善率 15% 以上を達成していること
    assert result.improved_percentage >= 15.0
    assert len(result.history) == 3  # cycle 0, 1, 2
    assert "サイクル2" in best_draft


@pytest.mark.asyncio
async def test_pdca_cycle_early_stopping_on_plateau():
    """Verify PDCA runner stops early when improvements plateau below min_improvement_delta."""
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    # Score sequence: 60.0 -> 61.0 -> 61.2 (delta < min_improvement_delta 1.5)
    specialists = [
        create_mock_specialist(n, [60.0, 61.0, 61.2, 61.3])
        for n in SPECIALIST_NAMES
    ]
    agg = AuditAggregator(specialists=specialists, weights=eq_w)

    async def mock_writer(ctx):
        return f"微小な修正ドラフト: {ctx.get('pdca_cycle')}"

    runner = ClosedLoopPDCARunner(
        aggregator=agg,
        writer=mock_writer,
        target_score=85.0,  # High target, won't reach
        max_cycles=4,
        min_improvement_delta=1.5,
    )

    _, result = await runner.run_pdca_cycle({"draft_text": "ドラフト"}, genre="general")
    assert result.converged is False
    # Stopped before max_cycles due to plateau
    assert result.cycle_number < 4


@pytest.mark.asyncio
async def test_pdca_event_bus_notification():
    """Verify PDCA completion event is published to event bus."""
    mock_bus = MagicMock()
    mock_bus.publish_async = AsyncMock()

    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    specialists = [
        create_mock_specialist(n, [80.0])  # Already high, 1-shot converge
        for n in SPECIALIST_NAMES
    ]
    agg = AuditAggregator(specialists=specialists, weights=eq_w)

    runner = ClosedLoopPDCARunner(
        aggregator=agg,
        writer=lambda c: "ドラフト",
        target_score=75.0,
        event_bus=mock_bus,
    )

    await runner.run_pdca_cycle({"draft_text": "ドラフト", "book_id": 99}, genre="fantasy")
    assert mock_bus.publish_async.called
    payload = mock_bus.publish_async.call_args[0][0].payload
    assert payload["event"] == "audit.pdca.completed"
    assert payload["book_id"] == 99
