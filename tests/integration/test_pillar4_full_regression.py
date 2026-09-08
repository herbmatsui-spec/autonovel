"""Full Regression Test Suite for Pillar 4: Closed-Loop PDCA & Commercial Quality (Step 70).

Verifies the end-to-end integration of all Pillar 4 components:
1. Specialist Anchors & Actionable Diffs
2. Score Calibration Engine & Sigmoid Scaling
3. Unified 5D BookScore Bridge & Breakdown
4. PDCA Directive Generation & Priority Ordering
5. Closed-Loop Revision & Convergence Detection
6. Dynamic DAG Replanning & Downstream Cancellation
7. Commercial Quality Benchmarking (85+ S-rank) & 7-Point Health Check
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# 1. Specialists & Anchors
from src.agents.specialists.anchors import (
    SPECIALIST_ANCHOR_PRESETS,
    get_anchor_preset,
)
from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    ActionableDiff,
)

# 2. Calibration & Aggregator
from src.services.score_calibrator import ScoreCalibrator
from src.services.audit_aggregator import AuditAggregator, SPECIALIST_NAMES

# 3. 5D Mapping & BookScore
from src.services.book_score_mapping import UnifiedBookScoreBridge
from src.services.book_score_service import BookScoreCalculator

# 4. Directives & PDCA
from src.services.pdca_directive import (
    PDCADirectiveGenerator,
    WritingDirective,
)
from src.services.pdca_cycle import ClosedLoopPDCARunner

# 5. DAG Replanning
from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.dag_replanning import DAGReplanningState

# 6. Commercial Benchmarks
from src.services.commercial_benchmarks import (
    CommercialBenchmarkJudge,
    CommercialQualityMetrics,
)


def test_specialist_anchors_and_actionable_diffs():
    """Verify that all 8 specialists have anchors and actionable diffs can be parsed."""
    assert len(SPECIALIST_ANCHOR_PRESETS) == 8
    for name in SPECIALIST_ANCHOR_PRESETS:
        preset = get_anchor_preset(name)
        assert preset is not None
        assert len(preset.anchors) == 3  # high, mid, low
        assert preset.get_by_tier("high") is not None
        assert preset.get_by_tier("mid") is not None
        assert preset.get_by_tier("low") is not None

    diff = ActionableDiff(
        location="第1章 冒頭",
        original_quote="彼は走った。",
        improved_suggestion="彼は泥濘む地面を蹴り、息を切らせて疾走した。",
        rationale="読者の身体感覚を刺激する動的な描写への改善。",
    )
    assert diff.location == "第1章 冒頭"
    assert "彼は走った。" in diff.original_quote
    diff_dict = diff.to_dict()
    assert "泥濘む地面" in diff_dict["improved_suggestion"]

    directive = PDCADirectiveGenerator.diff_to_directive(diff, "style", 45.0)
    assert directive.severity == "CRITICAL"
    assert "泥濘む地面" in directive.mandatory_instruction


def test_score_calibration_and_unified_5d_bridge():
    """Verify Bayesian calibration, sigmoid scaling, and 5D BookScore mapping."""
    calibrator = ScoreCalibrator()

    raw_scores = {
        "reader_hook": 50.0,
        "structure": 55.0,
        "character_depth": 52.0,
        "style": 60.0,
        "emotion_curve": 48.0,
        "consistency": 58.0,
        "theme": 54.0,
        "multimodal": 50.0,
    }

    # Calibrate raw scores using calibrate_all
    cal_res = calibrator.calibrate_all(raw_scores)
    calibrated_scores = cal_res["calibrated_scores"]
    assert len(calibrated_scores) == 8
    for score in calibrated_scores.values():
        assert 0.0 <= score <= 100.0

    # Map to 5D
    bridge = UnifiedBookScoreBridge()
    result_5d = bridge.map_to_5d(calibrated_scores, genre="isekai_fantasy")
    assert 0.0 <= result_5d.overall_score <= 100.0
    assert 0.0 <= result_5d.structure_score <= 100.0
    assert 0.0 <= result_5d.coherency_score <= 100.0
    assert 0.0 <= result_5d.reader_experience_score <= 100.0
    assert len(result_5d.contributions) == 5

    # Evaluate initial quality -> should be low / needing revision
    dim_dict = {
        "structure_score": result_5d.structure_score,
        "coherency_score": result_5d.coherency_score,
        "factual_grounding_score": result_5d.factual_grounding_score,
        "visual_textual_synergy_score": result_5d.visual_textual_synergy_score,
        "reader_experience_score": result_5d.reader_experience_score,
    }
    quality_before = CommercialBenchmarkJudge.evaluate_quality(
        result_5d.overall_score,
        dim_dict,
    )
    assert quality_before.is_commercial_ready is False


@pytest.mark.asyncio
async def test_closed_loop_pdca_convergence():
    """Verify closed loop revision improves text and converges."""
    def create_mock_specialist(name: str, scores: list[float]):
        s = MagicMock(spec=SpecialistAuditor)
        s.specialist_name = name
        idx = [0]

        async def _safe_audit(ctx):
            curr_idx = min(idx[0], len(scores) - 1)
            score = scores[curr_idx]
            idx[0] += 1
            return SpecialistAuditResult(
                specialist_name=name,
                score=score,
                confidence=0.9,
                actionable_diffs=[
                    ActionableDiff(
                        location="序盤",
                        original_quote="浅い描写",
                        improved_suggestion="深い描写",
                        rationale="没入感向上",
                    )
                ],
            )
        s._safe_audit = _safe_audit
        return s

    specialists = [
        create_mock_specialist(name, [60.0, 75.0, 88.0])
        for name in SPECIALIST_NAMES
    ]
    agg = AuditAggregator(specialists=specialists, weights={n: 0.125 for n in SPECIALIST_NAMES})

    async def mock_writer(ctx):
        cycle = ctx.get("pdca_cycle", 1)
        return f"改訂原稿 サイクル{cycle}: 描写を大幅に向上させました。"

    runner = ClosedLoopPDCARunner(
        aggregator=agg,
        writer=mock_writer,
        target_score=85.0,
        max_cycles=3,
        min_improvement_delta=1.0,
    )

    best_text, result = await runner.run_pdca_cycle({"draft_text": "初期原稿"})
    assert result.converged is True
    assert result.final_score >= 85.0
    assert result.improved_percentage >= 15.0
    assert len(result.history) >= 2


@pytest.mark.asyncio
async def test_dag_replanning_downstream_rollback():
    """Verify DAG replanning safely resets downstream tasks and enables retry."""
    event_bus = MagicMock()
    event_bus.publish_async = AsyncMock()

    scheduler = DAGScheduler(task_registry={
        "n1": lambda: "v1",
        "n2": lambda: "v2",
        "n3": lambda: "v3",
    }, event_bus=event_bus)

    graph = DAGGraph(dag_id="dag_regression")
    graph.add_node(DAGTaskNode(task_id="n1", func_name="n1", status="completed"))
    graph.add_node(DAGTaskNode(task_id="n2", func_name="n2", dependencies=["n1"], status="failed"))
    graph.add_node(DAGTaskNode(task_id="n3", func_name="n3", dependencies=["n2"], status="running"))

    state = await scheduler.replan_node(
        graph,
        target_node_id="n1",
        reason="Quality regression",
    )

    assert isinstance(state, DAGReplanningState)
    assert graph.nodes["n1"].status == "pending"
    assert graph.nodes["n2"].status == "pending"
    assert graph.nodes["n3"].status == "pending"
    assert graph.nodes["n1"].retry_count == 1
    assert state.trigger_node_id == "n1"
    assert event_bus.publish_async.called


def test_commercial_benchmark_health_check_complete():
    """Verify commercial evaluation logic and 7/7 subsystem health."""
    all_passed, checks = CommercialBenchmarkJudge.run_system_health_check()
    assert all_passed is True
    assert len(checks) == 7
    assert all(checks.values())
