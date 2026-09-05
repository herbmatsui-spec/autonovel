"""Anti-AI correction loop controller.

Phase 6 / Steps 56-65: Orchestrates the detect -> correct -> re-detect loop
until the text scores above a threshold or max iterations are reached.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from src.services.anti_ai.correction_pipeline import AntiAICorrector
from src.services.anti_ai.models import CorrectionHistory, ViolationSpan
from src.services.anti_ai.orchestrator import RuleBasedAntiAIDetector

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    """Final result after the correction loop terminates."""

    text: str
    final_score: float
    iterations: int
    history: list[CorrectionHistory] = field(default_factory=list)
    converged: bool = False

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "final_score": self.final_score,
            "iterations": self.iterations,
            "converged": self.converged,
            "history": [h.to_dict() for h in self.history],
        }


class AntiAILoopController:
    """Iteratively detect and correct AI fingerprints.

    Runs up to ``max_loops`` iterations of:
        1. Detect violations in current text
        2. Apply corrections
        3. Re-detect to verify improvement

    Terminates early if:
        - Score reaches or exceeds ``score_threshold``
        - No violations remain
        - No score improvement from previous iteration
    """

    def __init__(
        self,
        detector: RuleBasedAntiAIDetector | None = None,
        corrector: AntiAICorrector | None = None,
        max_loops: int = 5,
        score_threshold: float = 90.0,
        min_score_improvement: float = 1.0,
    ) -> None:
        self._detector = detector or RuleBasedAntiAIDetector()
        self._corrector = corrector or AntiAICorrector()
        self._max_loops = max_loops
        self._score_threshold = score_threshold
        self._min_score_improvement = min_score_improvement

    async def run(
        self,
        text: str,
        max_loops: int | None = None,
        score_threshold: float | None = None,
    ) -> LoopResult:
        """Run the correction loop on ``text``.

        Args:
            text: The text to correct.
            max_loops: Override default max iterations.
            score_threshold: Override default score threshold (0-100).

        Returns:
            LoopResult with final text, score, and iteration history.
        """
        max_loops = max_loops if max_loops is not None else self._max_loops
        score_threshold = score_threshold if score_threshold is not None else self._score_threshold

        current_text = text
        history: list[CorrectionHistory] = []
        previous_score = 0.0
        converged = False

        for iteration in range(1, max_loops + 1):
            result = self._detector.detect(current_text)
            current_score = result.total_score

            if current_score >= score_threshold:
                logger.info("Score threshold reached: %.1f >= %.1f", current_score, score_threshold)
                converged = True
                break

            if not result.violations:
                logger.info("No violations found - converged")
                converged = True
                break

            correction_result = self._corrector.correct(current_text, result.violations)

            output_score = current_score
            if correction_result.total_changes > 0:
                after_result = self._detector.detect(correction_result.text)
                output_score = after_result.total_score

            history.append(CorrectionHistory(
                iteration=iteration,
                input_score=current_score,
                output_score=output_score,
                violations_found=len(result.violations),
                violations_corrected=correction_result.total_changes,
                corrected_text=correction_result.text,
            ))

            score_improvement = current_score - previous_score
            if iteration > 1 and score_improvement < self._min_score_improvement:
                logger.info("Score improvement %.2f below threshold - stopping", score_improvement)
                break

            previous_score = current_score
            current_text = correction_result.text

            logger.debug(
                "Iteration %d: score=%.1f, violations=%d, changes=%d",
                iteration,
                current_score,
                len(result.violations),
                correction_result.total_changes,
            )

        final_result = self._detector.detect(current_text)

        return LoopResult(
            text=current_text,
            final_score=final_result.total_score,
            iterations=len(history),
            history=history,
            converged=converged,
        )

    def run_sync(
        self,
        text: str,
        max_loops: int | None = None,
        score_threshold: float | None = None,
    ) -> LoopResult:
        """Synchronous version of run()."""
        return asyncio.run(self.run(text, max_loops, score_threshold))


__all__ = ["AntiAILoopController", "LoopResult"]
