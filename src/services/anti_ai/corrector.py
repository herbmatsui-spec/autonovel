"""Auto-correction strategies for AI-fingerprint violations.

A :class:`BaseCorrector` knows how to rewrite one of the seven
categories. Given the original text and the violations returned by
the matching detector, it returns a corrected version of the text
together with metadata about what it changed.

Correctors are intentionally simple — they apply conservative
string-level rewrites (deletion, synonym substitution, light
re-ordering) and DO NOT call the LLM. The optional LLM sanity
check happens elsewhere (see :mod:`llm_sanity`).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.services.anti_ai.models import (
    AICategory,
    ViolationSpan,
)

logger = logging.getLogger(__name__)


@dataclass
class CorrectedText:
    """The result of a single correction pass.

    Attributes:
        text: the rewritten text.
        changes: count of violations that were actually rewritten.
        skipped: count of violations we deliberately left alone
            (e.g. no safe rule-based rewrite available).
    """

    text: str
    changes: int = 0
    skipped: int = 0
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text_length": len(self.text),
            "changes": self.changes,
            "skipped": self.skipped,
            "details": list(self.details),
        }


@dataclass
class CorrectionResult:
    """Aggregated result of a full correction pipeline run."""

    text: str
    total_changes: int = 0
    total_skipped: int = 0
    category_changes: dict[AICategory, int] = field(default_factory=dict)
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text_length": len(self.text),
            "total_changes": self.total_changes,
            "total_skipped": self.total_skipped,
            "category_changes": {k.value: v for k, v in self.category_changes.items()},
            "details": list(self.details),
        }


def _apply_replacements(
    text: str,
    replacements: list[tuple[int, int, str]],
) -> str:
    """Apply a list of (start, end, replacement) edits in one pass.

    Replacements MUST be non-overlapping and ordered by ``start``.
    We rebuild the string rather than mutating offsets because the
    replacement text can be a different length.
    """
    if not replacements:
        return text
    out: list[str] = []
    cursor = 0
    for start, end, repl in replacements:
        if start < cursor:
            logger.warning("Overlapping replacement: (%d,%d) after cursor %d", start, end, cursor)
            continue
        out.append(text[cursor:start])
        out.append(repl)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


class BaseCorrector(ABC):
    """Rewrite violations of one category."""

    category: AICategory

    def correct(self, text: str, violations: list[ViolationSpan]) -> CorrectedText:
        if not violations:
            return CorrectedText(text=text, changes=0, skipped=0)
        ours = [v for v in violations if v.category == self.category]
        if not ours:
            return CorrectedText(text=text, changes=0, skipped=0)
        try:
            edits = self._build_replacements(text, ours)
        except Exception as exc:
            logger.exception("Corrector %s failed: %s", self.category.value, exc)
            return CorrectedText(text=text, changes=0, skipped=len(ours))
        new_text = _apply_replacements(text, edits)
        return CorrectedText(
            text=new_text,
            changes=len(edits),
            skipped=len(ours) - len(edits),
            details=[{"start": s, "end": e, "replacement": r} for s, e, r in edits],
        )

    @abstractmethod
    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        """Return a list of non-overlapping edits.

        Each edit is ``(start, end, replacement)`` and the
        implementation MUST be deterministic.
        """


__all__ = [
    "BaseCorrector",
    "CorrectedText",
    "CorrectionResult",
    "_apply_replacements",
]
