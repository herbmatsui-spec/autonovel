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

    def lowest_dimension(self) -> str | None:
        """Return the specialist with the lowest score, or None if no data."""
        if not self.by_specialist:
            return None
        return min(self.by_specialist, key=self.by_specialist.get)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": round(self.overall, 2),
            "by_specialist": {k: round(v, 2) for k, v in self.by_specialist.items()},
            "missing": list(self.missing),
            "weights_used": {k: round(v, 4) for k, v in self.weights_used.items()},
            "lowest_dimension": self.lowest_dimension(),
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

    @classmethod
    def from_registry(
        cls,
        registry: Mapping[str, SpecialistAuditor],
        weights: Mapping[str, float],
        event_bus: Any | None = None,
    ) -> "AuditAggregator":
        specialists = list(registry.values())
        return cls(specialists=specialists, weights=weights, event_bus=event_bus)

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

    def aggregate(self) -> BookScoreResult:
        """Compute weighted overall score from the latest run_all results."""
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
        return BookScoreResult(
            overall=overall,
            by_specialist=by_specialist,
            missing=missing,
            weights_used=weights_used,
            raw=dict(self._results),
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