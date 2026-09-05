"""Rule-based anti-AI orchestrator.

Runs every registered detector against the input text and combines
their results into a single :class:`AntiAIDetectionResult`. This is
the synchronous, LLM-free path used by default.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config.anti_ai_config import AntiAIConfig
from src.services.anti_ai.detectors import RULE_DETECTORS
from src.services.anti_ai.models import (
    DEFAULT_CATEGORY_WEIGHTS,
    AICategory,
    AntiAIDetectionResult,
    ViolationSpan,
    compute_total_score,
)
from src.services.anti_ai.rule_detector import BaseRuleDetector

logger = logging.getLogger(__name__)


class RuleBasedAntiAIDetector:
    """Run every registered rule-based detector and aggregate results.

    Detectors are looked up from :data:`RULE_DETECTORS` so adding a
    new category only requires registering a new class there.
    """

    def __init__(
        self,
        config: AntiAIConfig | None = None,
        detectors: list[BaseRuleDetector] | None = None,
    ) -> None:
        self.config = config
        if detectors is not None:
            self._detectors: dict[AICategory, BaseRuleDetector] = {
                d.category: d for d in detectors
            }
        else:
            self._detectors = {
                cat: cls(config=config) for cat, cls in RULE_DETECTORS.items()
            }

    @property
    def detectors(self) -> dict[AICategory, BaseRuleDetector]:
        return dict(self._detectors)

    def detect(self, text: str) -> AntiAIDetectionResult:
        """Run every detector synchronously and aggregate.

        Order: each detector runs to completion before the next, so
        a bad detector cannot corrupt the others' state. Tests can
        pass a pre-built ``detectors`` list to inject mocks.
        """
        if not text or not text.strip():
            return AntiAIDetectionResult(
                category_scores={c: 100.0 for c in AICategory},
                total_score=100.0,
                violations=[],
                method="rule_based",
            )

        all_violations: list[ViolationSpan] = []
        category_scores: dict[AICategory, float] = {}

        for cat in AICategory:
            detector = self._detectors.get(cat)
            if detector is None:
                category_scores[cat] = 100.0
                continue
            try:
                violations = detector.detect(text)
            except Exception as exc:  # pragma: no cover - safety net
                logger.exception("Detector %s failed: %s", cat.value, exc)
                category_scores[cat] = 50.0
                continue
            all_violations.extend(violations)
            try:
                category_scores[cat] = detector.score_from_violations(text, violations)
            except Exception as exc:  # pragma: no cover
                logger.exception("Scoring %s failed: %s", cat.value, exc)
                category_scores[cat] = 50.0

        # Sort all violations by start for stable downstream use.
        all_violations.sort(key=lambda v: v.start)

        total = compute_total_score(category_scores, DEFAULT_CATEGORY_WEIGHTS)
        return AntiAIDetectionResult(
            category_scores=category_scores,
            total_score=total,
            violations=all_violations,
            method="rule_based",
        )

    async def adetect(self, text: str) -> AntiAIDetectionResult:
        """Async wrapper. Currently each detector is CPU-bound so we
        off-load to a thread, but if a future detector becomes I/O
        bound (e.g. uses a local model) this method is the seam."""
        return await asyncio.to_thread(self.detect, text)


__all__ = ["RuleBasedAntiAIDetector"]
