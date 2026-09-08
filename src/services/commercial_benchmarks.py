"""Commercial Quality Benchmarks & Health Check Engine (Phase 4 / Part 6).

Defines standards for Commercial Publication (85+), Web Serial Hit (75+),
fatal flaw cutoffs (no dimension < 60), PDCA improvement rate (>= 15%),
and 7-point system health verification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from src.services.book_score_mapping import BOOK_SCORE_DIMENSIONS, BASE_TRANSFORMATION_MATRIX
from src.services.pdca_directive import WritingDirective
from src.agents.specialists.anchors import ANCHOR_PRESETS

logger = logging.getLogger(__name__)


@dataclass
class CommercialQualityMetrics:
    """Comprehensive commercial viability and maturity metrics (Step 61)."""
    overall_score: float
    dimension_scores: dict[str, float]
    specialist_scores: dict[str, float]
    is_commercial_ready: bool  # >= 85.0 and no dimension < 70
    is_web_hit_ready: bool  # >= 75.0 and no dimension < 65
    has_no_fatal_flaws: bool  # no dimension < 60.0
    improvement_rate: float = 0.0  # percentage gain from PDCA
    health_check_passed: bool = False
    health_check_details: dict[str, bool] = field(default_factory=dict)
    rank: str = "C"
    evaluation_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "rank": self.rank,
            "is_commercial_ready": self.is_commercial_ready,
            "is_web_hit_ready": self.is_web_hit_ready,
            "has_no_fatal_flaws": self.has_no_fatal_flaws,
            "improvement_rate": round(self.improvement_rate, 2),
            "health_check_passed": self.health_check_passed,
            "health_check_details": self.health_check_details,
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "specialist_scores": {k: round(v, 2) for k, v in self.specialist_scores.items()},
            "evaluation_summary": self.evaluation_summary,
        }


class CommercialBenchmarkJudge:
    """Automated judge for commercial publication, web hit, and PDCA benchmarks."""

    COMMERCIAL_THRESHOLD = 85.0
    COMMERCIAL_DIM_MIN = 70.0

    WEB_HIT_THRESHOLD = 75.0
    WEB_HIT_DIM_MIN = 65.0

    FATAL_FLAW_THRESHOLD = 60.0
    TARGET_PDCA_IMPROVEMENT_RATE = 15.0

    @classmethod
    def evaluate_quality(
        cls,
        overall_score: float,
        dimension_scores: Mapping[str, float],
        specialist_scores: Mapping[str, float] | None = None,
        improvement_rate: float = 0.0,
    ) -> CommercialQualityMetrics:
        """Evaluate text maturity against commercial and web hit standards (Steps 62-64)."""
        dim_dict = dict(dimension_scores)
        spec_dict = dict(specialist_scores or {})

        # Step 63: Fatal flaw check (no dimension below 60.0)
        min_dim_score = min(dim_dict.values()) if dim_dict else overall_score
        has_no_fatal_flaws = min_dim_score >= cls.FATAL_FLAW_THRESHOLD

        # Step 62: Standard checks
        is_commercial = (
            overall_score >= cls.COMMERCIAL_THRESHOLD
            and min_dim_score >= cls.COMMERCIAL_DIM_MIN
        )
        is_web_hit = (
            overall_score >= cls.WEB_HIT_THRESHOLD
            and min_dim_score >= cls.WEB_HIT_DIM_MIN
        )

        # Grade ranking
        if is_commercial:
            rank = "S"
            summary = "【Sランク】商業出版水準達成。文体・構成・牽引力ともに極めて高い完成度。"
        elif is_web_hit:
            rank = "A"
            summary = "【Aランク】Web連載人気水準達成。商業化有力候補の引き込み力と感情展開。"
        elif overall_score >= 65.0:
            rank = "B"
            summary = "【Bランク】標準的エンタメ品質。プロット展開または文体の部分修正推奨。"
        elif overall_score >= 50.0:
            rank = "C"
            summary = "【Cランク】要改善。読者フックまたは感情起伏に明確な課題。"
        else:
            rank = "D"
            summary = "【Dランク】抜本的再執筆推奨。基礎構造または論理的一貫性の欠落。"

        return CommercialQualityMetrics(
            overall_score=overall_score,
            dimension_scores=dim_dict,
            specialist_scores=spec_dict,
            is_commercial_ready=is_commercial,
            is_web_hit_ready=is_web_hit,
            has_no_fatal_flaws=has_no_fatal_flaws,
            improvement_rate=improvement_rate,
            rank=rank,
            evaluation_summary=summary,
        )

    @classmethod
    def validate_pdca_improvement(
        cls,
        before_score: float,
        after_score: float,
        target_rate: float | None = None,
    ) -> tuple[bool, float]:
        """Validate if PDCA cycle met the target score improvement percentage (Step 64)."""
        req_rate = target_rate or cls.TARGET_PDCA_IMPROVEMENT_RATE
        delta = after_score - before_score
        rate = (delta / max(1.0, before_score)) * 100.0
        passed = rate >= req_rate
        return passed, round(rate, 2)

    @classmethod
    def run_system_health_check(cls) -> tuple[bool, dict[str, bool]]:
        """Run full 7-point health check across the Pillar 4 PDCA integration (Step 65)."""
        checks: dict[str, bool] = {}

        # 1. Specialist Anchors
        try:
            from src.agents.specialists.anchors import ANCHOR_PRESETS
            checks["1_anchors_valid"] = len(ANCHOR_PRESETS) == 8
        except Exception:
            checks["1_anchors_valid"] = False

        # 2. Score Calibration Engine
        try:
            from src.services.score_calibrator import ScoreCalibrator
            cal = ScoreCalibrator()
            sc, _ = cal.calibrate_single("reader_hook", 80.0)
            checks["2_calibration_engine_valid"] = 10.0 <= sc <= 98.0
        except Exception:
            checks["2_calibration_engine_valid"] = False

        # 3. Unified 5D Bridge
        try:
            from src.services.book_score_mapping import UnifiedBookScoreBridge
            bridge = UnifiedBookScoreBridge()
            u5d = bridge.map_to_5d({n: 70.0 for n in ANCHOR_PRESETS})
            checks["3_unified_5d_bridge_valid"] = u5d.overall_score == 70.0
        except Exception:
            checks["3_unified_5d_bridge_valid"] = False

        # 4. Actionable Diff & Directives
        try:
            from src.agents.specialist_auditor_base import ActionableDiff
            from src.services.pdca_directive import PDCADirectiveGenerator
            diff = ActionableDiff(location="冒頭", original_quote="A", improved_suggestion="B", rationale="C")
            d = PDCADirectiveGenerator.diff_to_directive(diff, "structure", 45.0)
            checks["4_directives_actionable_valid"] = d.severity == "CRITICAL"
        except Exception:
            checks["4_directives_actionable_valid"] = False

        # 5. Closed-Loop PDCA Runner
        try:
            from src.services.pdca_cycle import ClosedLoopPDCARunner
            checks["5_pdca_runner_valid"] = hasattr(ClosedLoopPDCARunner, "run_pdca_cycle")
        except Exception:
            checks["5_pdca_runner_valid"] = False

        # 6. DAG Replanner Engine
        try:
            from src.backend.tasks.dag_replanning import DAGReplanner
            from src.backend.tasks.dag_models import DAGGraph
            g = DAGGraph(dag_id="test")
            downstream = DAGReplanner.get_downstream_tasks(g, "none")
            checks["6_dag_replanner_valid"] = isinstance(downstream, list)
        except Exception:
            checks["6_dag_replanner_valid"] = False

        # 7. Commercial Benchmarks Judge
        try:
            metrics = cls.evaluate_quality(88.0, {"structure_score": 85.0, "coherency_score": 85.0})
            checks["7_commercial_judge_valid"] = metrics.is_commercial_ready is True
        except Exception:
            checks["7_commercial_judge_valid"] = False

        all_passed = all(checks.values()) and len(checks) == 7
        return all_passed, checks


__all__ = [
    "CommercialQualityMetrics",
    "CommercialBenchmarkJudge",
]
