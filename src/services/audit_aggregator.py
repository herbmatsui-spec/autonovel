"""Audit Aggregator service.

Phase 2 / Guideline #3: Aggregates 8 specialist auditors with weighted
scoring, weighted by genre and writing phase.

This module only contains the core aggregation logic. Run / orchestration
is added in Step 18 once specialists are registered.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from src.agents.specialist_auditor_base import (
    SpecialistAuditResult,
    SpecialistAuditor,
)

logger = logging.getLogger(__name__)

SPECIALIST_NAMES: tuple[str, ...] = (
    "consistency",
    "creativity",
    "reader_hook",
    "emotion_curve",
    "style",
    "factual",
    "structure",
    "multimodal",
)

WEIGHT_TOLERANCE = 1e-6


@dataclass
class BookScoreResult:
    overall: float
    by_specialist: dict[str, float]
    missing: list[str] = field(default_factory=list)
    weights_used: dict[str, float] = field(default_factory=dict)
    raw: dict[str, SpecialistAuditResult] = field(default_factory=dict)
    calibrated_overall: float | None = None
    calibrated_by_specialist: dict[str, float] = field(default_factory=dict)
    calibration_meta: dict[str, Any] = field(default_factory=dict)
    outliers: list[str] = field(default_factory=list)
    variance_penalty: float = 0.0

    def lowest_dimension(self, use_calibrated: bool = True) -> str | None:
        """Return the specialist with the lowest score, or None if no data."""
        target_dict = (
            self.calibrated_by_specialist
            if (use_calibrated and self.calibrated_by_specialist)
            else self.by_specialist
        )
        if not target_dict:
            return None
        return min(target_dict, key=target_dict.get)

    def get_actionable_diffs_for(self, dimension: str) -> list[Any]:
        """Return actionable diffs from a specific specialist."""
        if not dimension or dimension not in self.raw:
            return []
        res = self.raw[dimension]
        return list(getattr(res, "actionable_diffs", []))

    def all_actionable_diffs(self) -> list[Any]:
        """Return all actionable diffs across all specialists."""
        diffs = []
        for res in self.raw.values():
            diffs.extend(getattr(res, "actionable_diffs", []))
        return diffs

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": round(self.overall, 2),
            "calibrated_overall": round(self.calibrated_overall, 2) if self.calibrated_overall is not None else None,
            "by_specialist": {k: round(v, 2) for k, v in self.by_specialist.items()},
            "calibrated_by_specialist": {k: round(v, 2) for k, v in self.calibrated_by_specialist.items()},
            "missing": list(self.missing),
            "weights_used": {k: round(v, 4) for k, v in self.weights_used.items()},
            "lowest_dimension": self.lowest_dimension(),
            "outliers": list(self.outliers),
            "variance_penalty": round(self.variance_penalty, 2),
            "actionable_diffs_count": len(self.all_actionable_diffs()),
        }


def validate_weights(weights: Mapping[str, float]) -> None:
    """Ensure weights cover all 8 specialists and sum to 1.0."""
    missing = [n for n in SPECIALIST_NAMES if n not in weights]
    if missing:
        raise ValueError(f"Missing weights for specialists: {missing}")
    total = sum(weights[n] for n in SPECIALIST_NAMES)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(
            f"Weights must sum to 1.0 (got {total:.6f}); adjust the YAML"
        )


def renormalize(
    weights: Mapping[str, float], present: Sequence[str]
) -> dict[str, float]:
    """Re-normalize weights so the present specialists sum to 1.0.

    Missing specialists are removed; weights of present specialists are
    rescaled proportionally.
    """
    if not present:
        return {}
    present_weights = {n: float(weights.get(n, 0.0)) for n in present}
    total = sum(present_weights.values())
    if total <= 0:
        # Equal weight fallback
        eq = 1.0 / len(present)
        return {n: eq for n in present}
    return {n: w / total for n, w in present_weights.items()}


class AuditAggregator:
    """Run 8 specialist auditors in parallel and aggregate their scores.

    Usage::

        agg = AuditAggregator.from_registry(registry, weights=weights)
        await agg.run_all(ctx)
        result = agg.aggregate()
    """

    def __init__(
        self,
        specialists: Sequence[SpecialistAuditor],
        weights: Mapping[str, float],
        event_bus: Any | None = None,
        calibrator: Any | None = None,
    ) -> None:
        self.weights: dict[str, float] = {n: float(weights.get(n, 0.0)) for n in SPECIALIST_NAMES}
        validate_weights(self.weights)
        self.specialists: dict[str, SpecialistAuditor] = {
            s.specialist_name: s for s in specialists if s.specialist_name
        }
        missing = [n for n in SPECIALIST_NAMES if n not in self.specialists]
        if missing:
            logger.warning(
                "AuditAggregator: missing specialists %s will be reported as missing",
                missing,
            )
        self.event_bus = event_bus
        self._results: dict[str, SpecialistAuditResult] = {}
        if calibrator is None:
            try:
                from src.services.score_calibrator import ScoreCalibrator
                self.calibrator = ScoreCalibrator()
            except Exception:
                self.calibrator = None
        else:
            self.calibrator = calibrator

    @classmethod
    def from_registry(
        cls,
        registry: Mapping[str, SpecialistAuditor],
        weights: Mapping[str, float],
        event_bus: Any | None = None,
        calibrator: Any | None = None,
    ) -> "AuditAggregator":
        specialists = list(registry.values())
        return cls(specialists=specialists, weights=weights, event_bus=event_bus, calibrator=calibrator)

    @property
    def results(self) -> dict[str, SpecialistAuditResult]:
        return dict(self._results)

    async def run_all(self, ctx: dict[str, Any]) -> dict[str, SpecialistAuditResult]:
        """Run all registered specialists in parallel via asyncio.gather."""
        self._results = {}

        async def _run(name: str, sp: SpecialistAuditor) -> tuple[str, SpecialistAuditResult]:
            try:
                await self._publish_started(name, ctx)
                result = await sp._safe_audit(ctx)
                await self._publish_completed(name, result, ctx)
                return name, result
            except Exception as e:
                logger.exception("Specialist %s crashed unexpectedly", name)
                return name, SpecialistAuditResult(
                    specialist_name=name,
                    score=0.0,
                    error=repr(e),
                    degraded=True,
                )

        tasks = [_run(n, s) for n, s in self.specialists.items()]
        pairs = await asyncio.gather(*tasks, return_exceptions=False)
        for name, result in pairs:
            self._results[name] = result
        return self._results

    def aggregate(
        self,
        genre: str = "general",
        apply_calibration: bool = True,
    ) -> BookScoreResult:
        """Compute weighted overall score with calibration, outlier detection, and variance penalty."""
        present: list[str] = []
        missing: list[str] = []
        for n in SPECIALIST_NAMES:
            if n not in self._results:
                missing.append(n)
                continue
            r = self._results[n]
            if r.error is not None and r.degraded and r.score == 0.0:
                # Treat fully-crashed specialists as missing for aggregation.
                missing.append(n)
                continue
            present.append(n)

        if not present:
            return BookScoreResult(
                overall=0.0,
                by_specialist={},
                missing=list(SPECIALIST_NAMES),
                weights_used={},
                raw={},
            )

        weights_used = renormalize(self.weights, present)
        overall = sum(self._results[n].score * weights_used[n] for n in present)
        by_specialist = {n: self._results[n].score for n in present}

        calibrated_overall: float | None = overall
        calibrated_by_specialist = dict(by_specialist)
        calibration_meta: dict[str, Any] = {}
        outliers: list[str] = []
        variance_penalty: float = 0.0

        # Step 19-22: スコアキャリブレーション・外れ値検出・分散ペナルティ
        if apply_calibration and self.calibrator is not None:
            cal_input = {}
            for n in present:
                res = self._results[n]
                conf = getattr(res, "confidence", 1.0)
                cal_input[n] = {"score": res.score, "confidence": conf}

            cal_output = self.calibrator.calibrate_all(cal_input, genre=genre)
            calibrated_by_specialist = cal_output.get("calibrated_scores", by_specialist)
            calibration_meta = cal_output.get("metadata", {})
            outliers = cal_output.get("outliers", [])

            if outliers:
                logger.warning(
                    "AuditAggregator: detected score outliers for specialists %s (genre=%s)",
                    outliers, genre,
                )

            # キャリブレーション後総合得点
            calibrated_overall = sum(
                calibrated_by_specialist.get(n, 50.0) * weights_used[n] for n in present
            )

            # Step 22: 専門家間スコアの分散ペナルティ計算
            if len(present) >= 3:
                import statistics
                scores_list = [calibrated_by_specialist[n] for n in present]
                stdev = statistics.stdev(scores_list)
                if stdev > 18.0:
                    variance_penalty = round((stdev - 18.0) * 0.5, 2)
                    calibrated_overall = max(10.0, calibrated_overall - variance_penalty)

        return BookScoreResult(
            overall=round(overall, 2),
            by_specialist=by_specialist,
            missing=missing,
            weights_used=weights_used,
            raw=dict(self._results),
            calibrated_overall=round(calibrated_overall, 2) if calibrated_overall is not None else None,
            calibrated_by_specialist=calibrated_by_specialist,
            calibration_meta=calibration_meta,
            outliers=outliers,
            variance_penalty=variance_penalty,
        )

    async def _publish_started(self, name: str, ctx: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        try:
            from src.agents.event_bus import AgentEvent

            await self.event_bus.publish_async(
                AgentEvent(
                    agent=f"audit.specialist.{name}",
                    payload={
                        "event": "audit.specialist.started",
                        "specialist": name,
                        "book_id": ctx.get("book_id"),
                        "chapter_number": ctx.get("chapter_number"),
                    },
                    correlation_id=str(ctx.get("correlation_id", "unknown")),
                )
            )
        except Exception:
            pass

    async def _publish_completed(
        self, name: str, result: SpecialistAuditResult, ctx: dict[str, Any]
    ) -> None:
        if not self.event_bus:
            return
        try:
            from src.agents.event_bus import AgentEvent

            # Extract weight variant from context or result feedback
            weight_variant = ctx.get("weight_variant") or result.feedback.get("weight_variant", "unknown")

            await self.event_bus.publish_async(
                AgentEvent(
                    agent=f"audit.specialist.{name}",
                    payload={
                        "event": "audit.specialist.completed",
                        "specialist": name,
                        "book_id": ctx.get("book_id"),
                        "chapter_number": ctx.get("chapter_number"),
                        "score": result.score,
                        "degraded": result.degraded,
                        "error": result.error,
                        "confidence": result.confidence,
                        "reasoning_trace": result.reasoning_trace,
                        "weight_variant": weight_variant,
                    },
                    correlation_id=str(ctx.get("correlation_id", "unknown")),
                )
            )
        except Exception:
            pass

    async def publish_aggregated_metrics(
        self,
        book_score: BookScoreResult,
        ctx: dict[str, Any],
        min_pass_score: float = 70.0,
    ) -> None:
        """Publish aggregated audit metrics for A/B test analysis."""
        if not self.event_bus:
            return
        try:
            from src.agents.event_bus import AgentEvent

            weight_variant = ctx.get("weight_variant", "unknown")
            genre = ctx.get("genre", "unknown")
            phase = ctx.get("phase", "unknown")

            await self.event_bus.publish_async(
                AgentEvent(
                    agent="audit.aggregated",
                    payload={
                        "event": "audit.aggregated",
                        "book_id": ctx.get("book_id"),
                        "chapter_number": ctx.get("chapter_number"),
                        "weight_variant": weight_variant,
                        "genre": genre,
                        "phase": phase,
                        "overall_score": book_score.overall,
                        "calibrated_overall_score": book_score.calibrated_overall,
                        "specialist_scores": book_score.by_specialist,
                        "calibrated_specialist_scores": book_score.calibrated_by_specialist,
                        "missing_specialists": book_score.missing,
                        "weights_used": book_score.weights_used,
                        "outliers": book_score.outliers,
                        "variance_penalty": book_score.variance_penalty,
                        "regeneration_triggered": (
                            (book_score.calibrated_overall if book_score.calibrated_overall is not None else book_score.overall)
                            < min_pass_score
                        ),
                        "lowest_dimension": book_score.lowest_dimension(),
                    },
                    correlation_id=str(ctx.get("correlation_id", "unknown")),
                )
            )
        except Exception:
            pass


__all__ = [
    "AuditAggregator",
    "BookScoreResult",
    "SPECIALIST_NAMES",
    "validate_weights",
    "renormalize",
]