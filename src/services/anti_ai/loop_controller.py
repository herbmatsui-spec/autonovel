"""Anti-AI correction loop controller.

Phase 6 / Steps 56-65: Orchestrates the detect -> correct -> re-detect loop
until the text scores above a threshold or max iterations are reached.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

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
        - Score improvement is below threshold for consecutive iterations (with backoff)
    """

    def __init__(
        self,
        detector: RuleBasedAntiAIDetector | None = None,
        corrector: AntiAICorrector | None = None,
        max_loops: int | None = None,
        score_threshold: float | None = None,
        min_score_improvement: float | None = None,
        backoff_base: float | None = None,
        backoff_max: float | None = None,
        config: Any = None,
    ) -> None:
        self._detector = detector or RuleBasedAntiAIDetector()
        self._corrector = corrector or AntiAICorrector()

        if config is not None:
            loop_cfg = getattr(config, "loop", None)
            if loop_cfg:
                self._max_loops = max_loops if max_loops is not None else getattr(loop_cfg, "max_iterations", 5)
                self._score_threshold = score_threshold if score_threshold is not None else getattr(loop_cfg, "stop_threshold", 90.0)
                self._min_score_improvement = min_score_improvement if min_score_improvement is not None else getattr(loop_cfg, "min_improvement", 2.0)
                self._backoff_base = backoff_base if backoff_base is not None else getattr(loop_cfg, "backoff_base_seconds", 2.0)
            else:
                self._max_loops = max_loops if max_loops is not None else 5
                self._score_threshold = score_threshold if score_threshold is not None else 90.0
                self._min_score_improvement = min_score_improvement if min_score_improvement is not None else 2.0
                self._backoff_base = backoff_base if backoff_base is not None else 2.0
        else:
            self._max_loops = max_loops if max_loops is not None else 5
            self._score_threshold = score_threshold if score_threshold is not None else 90.0
            self._min_score_improvement = min_score_improvement if min_score_improvement is not None else 2.0
            self._backoff_base = backoff_base if backoff_base is not None else 2.0
        self._backoff_max = backoff_max if backoff_max is not None else 10.0

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
        previous_output_score = 0.0
        converged = False
        backoff_iterations = 0

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

            score_improvement = output_score - previous_output_score

            history.append(CorrectionHistory(
                iteration=iteration,
                input_score=current_score,
                output_score=output_score,
                violations_found=len(result.violations),
                violations_corrected=correction_result.total_changes,
                corrected_text=correction_result.text,
            ))

            if iteration > 1 and score_improvement < self._min_score_improvement:
                backoff_iterations += 1
                if backoff_iterations >= 2:
                    backoff_time = min(self._backoff_base ** (backoff_iterations - 1), self._backoff_max)
                    logger.info("Score improvement %.2f below threshold - backing off for %.1f seconds", score_improvement, backoff_time)
                    await asyncio.sleep(backoff_time)
            else:
                backoff_iterations = 0

            previous_output_score = output_score
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
