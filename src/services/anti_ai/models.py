"""Anti-AI detection data models.

Defines the data structures used by the rule-based detectors, the
LLM-optional sanity checker, and the correction loop controller.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class AICategory(str, enum.Enum):
    """The 7 categories of AI-generated fingerprints we scan for."""

    TRANSITION_OVERUSE = "TRANSITION_OVERUSE"
    SAME_STRUCTURE = "SAME_STRUCTURE"
    DIRECT_EMOTION = "DIRECT_EMOTION"
    HEDGING_PATTERNS = "HEDGING_PATTERNS"
    TEMPLATE_PHRASES = "TEMPLATE_PHRASES"
    UNIFORM_PARAGRAPH = "UNIFORM_PARAGRAPH"
    GENERIC_VOCABULARY = "GENERIC_VOCABULARY"


class Severity(str, enum.Enum):
    """How severe a single violation is.

    CRITICAL ⇒ mandatory rewrite; LOW ⇒ advisory only.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Per-category default severity. Used when the detector does not
# override it based on the local context.
DEFAULT_SEVERITY: dict[AICategory, Severity] = {
    AICategory.TRANSITION_OVERUSE: Severity.MEDIUM,
    AICategory.SAME_STRUCTURE: Severity.HIGH,
    AICategory.DIRECT_EMOTION: Severity.MEDIUM,
    AICategory.HEDGING_PATTERNS: Severity.MEDIUM,
    AICategory.TEMPLATE_PHRASES: Severity.HIGH,
    AICategory.UNIFORM_PARAGRAPH: Severity.LOW,
    AICategory.GENERIC_VOCABULARY: Severity.LOW,
}


@dataclass
class ViolationSpan:
    """A single detected violation in the source text.

    Attributes:
        category: which AICategory was triggered.
        start: inclusive character offset of the violation.
        end: exclusive character offset.
        matched_text: the literal substring that matched.
        severity: how severe this particular hit is.
        suggestion: optional replacement text proposed by the rule
            or by the LLM sanity-check step.
    """

    category: AICategory
    start: int
    end: int
    matched_text: str
    severity: Severity = Severity.MEDIUM
    suggestion: str | None = None

    @property
    def length(self) -> int:
        return max(0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "start": self.start,
            "end": self.end,
            "matched_text": self.matched_text,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
        }


# Default category weights used when computing the total score. A
# higher weight means the category contributes more to the total.
DEFAULT_CATEGORY_WEIGHTS: dict[AICategory, float] = {
    AICategory.TRANSITION_OVERUSE: 1.0,
    AICategory.SAME_STRUCTURE: 1.5,
    AICategory.DIRECT_EMOTION: 1.0,
    AICategory.HEDGING_PATTERNS: 0.8,
    AICategory.TEMPLATE_PHRASES: 1.2,
    AICategory.UNIFORM_PARAGRAPH: 0.6,
    AICategory.GENERIC_VOCABULARY: 0.7,
}


@dataclass
class AntiAIDetectionResult:
    """The aggregate result of a single detection run.

    ``total_score`` is on a 0-100 scale where 100 means "no AI
    fingerprints detected" and 0 means "every category is at its
    worst".

    ``category_scores`` is normalised 0-100 per category.
    """

    category_scores: dict[AICategory, float] = field(default_factory=dict)
    total_score: float = 100.0
    violations: list[ViolationSpan] = field(default_factory=list)
    method: str = "rule_based"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_scores": {k.value: round(v, 2) for k, v in self.category_scores.items()},
            "total_score": round(self.total_score, 2),
            "violations": [v.to_dict() for v in self.violations],
            "method": self.method,
        }


@dataclass
class CorrectionHistory:
    """One iteration of the correction loop.

    Used by :class:`AntiAILoopController` to keep a per-call audit
    trail so we can report progress, debug regressions and feed
    Prometheus.
    """

    iteration: int
    input_score: float
    output_score: float
    violations_found: int
    violations_corrected: int
    corrected_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "input_score": round(self.input_score, 2),
            "output_score": round(self.output_score, 2),
            "violations_found": self.violations_found,
            "violations_corrected": self.violations_corrected,
        }


def normalise_score(raw: float, floor: float = 0.0, ceiling: float = 100.0) -> float:
    """Clamp ``raw`` into the ``[floor, ceiling]`` interval.

    Used by detectors so we never return a score outside the
    documented range, regardless of bug-induced arithmetic.
    """
    if raw < floor:
        return floor
    if raw > ceiling:
        return ceiling
    return float(raw)


def compute_total_score(
    category_scores: dict[AICategory, float],
    weights: dict[AICategory, float] | None = None,
) -> float:
    """Weighted average of ``category_scores`` mapped to 0-100.

    Each category score is expected to already be in [0, 100]. A
    category with no score is treated as 100 (no violation detected).

    Note: to get a true 0.0 you must explicitly pass every category
    with score 0.0; missing keys are treated as "clean" (100).
    """
    w = weights or DEFAULT_CATEGORY_WEIGHTS
    if not w:
        return 100.0
    total_w = 0.0
    total = 0.0
    for cat, weight in w.items():
        score = category_scores.get(cat, 100.0)
        total += score * weight
        total_w += weight
    if total_w <= 0:
        return 100.0
    return normalise_score(total / total_w, 0.0, 100.0)


__all__ = [
    "AICategory",
    "Severity",
    "DEFAULT_SEVERITY",
    "DEFAULT_CATEGORY_WEIGHTS",
    "ViolationSpan",
    "AntiAIDetectionResult",
    "CorrectionHistory",
    "normalise_score",
    "compute_total_score",
]
