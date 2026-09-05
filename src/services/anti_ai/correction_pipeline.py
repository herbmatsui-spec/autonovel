"""Correction pipeline that orchestrates all correctors.

This module provides the :class:`AntiAICorrector` class that applies
all registered correctors in sequence to produce a fully corrected text.
"""

from __future__ import annotations

from src.services.anti_ai.corrector import BaseCorrector, CorrectionResult
from src.services.anti_ai.models import AICategory, ViolationSpan


CORRECTORS: dict[AICategory, BaseCorrector] | None = None


def _get_correctors() -> dict[AICategory, BaseCorrector]:
    global CORRECTORS
    if CORRECTORS is None:
        from src.services.anti_ai.correctors import (
            TransitionOveruseCorrector,
            SameStructureCorrector,
            DirectEmotionCorrector,
            HedgingPatternsCorrector,
            TemplatePhrasesCorrector,
            UniformParagraphCorrector,
            GenericVocabularyCorrector,
        )

        CORRECTORS = {
            AICategory.TRANSITION_OVERUSE: TransitionOveruseCorrector(),
            AICategory.SAME_STRUCTURE: SameStructureCorrector(),
            AICategory.DIRECT_EMOTION: DirectEmotionCorrector(),
            AICategory.HEDGING_PATTERNS: HedgingPatternsCorrector(),
            AICategory.TEMPLATE_PHRASES: TemplatePhrasesCorrector(),
            AICategory.UNIFORM_PARAGRAPH: UniformParagraphCorrector(),
            AICategory.GENERIC_VOCABULARY: GenericVocabularyCorrector(),
        }
    return CORRECTORS


class AntiAICorrector:
    """Pipeline that applies all registered correctors in category order.

    Given a text and violations from the detector, this class applies
    the correctors in sequence and returns the fully corrected text.
    """

    def __init__(self, correctors: dict[AICategory, BaseCorrector] | None = None) -> None:
        self._correctors = correctors if correctors is not None else _get_correctors()

    def correct(self, text: str, violations: list[ViolationSpan]) -> CorrectionResult:
        current_text = text
        total_changes = 0
        total_skipped = 0
        category_changes: dict[AICategory, int] = {}
        all_details: list[dict] = []

        for category in AICategory:
            corrector = self._correctors.get(category)
            if corrector is None:
                continue
            ours = [v for v in violations if v.category == category]
            if not ours:
                continue
            result = corrector.correct(current_text, ours)
            current_text = result.text
            total_changes += result.changes
            total_skipped += result.skipped
            if result.changes > 0:
                category_changes[category] = result.changes
            all_details.extend(result.details)

        return CorrectionResult(
            text=current_text,
            total_changes=total_changes,
            total_skipped=total_skipped,
            category_changes=category_changes,
            details=all_details,
        )


__all__ = ["AntiAICorrector", "CORRECTORS"]
