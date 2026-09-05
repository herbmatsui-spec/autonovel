"""Abstract base class for rule-based anti-AI detectors.

Each detector is responsible for ONE of the seven AICategory values
and must implement :meth:`detect`. Detectors are stateless (apart
from the immutable config) so the same instance can be reused
across many detection calls and across processes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.config.anti_ai_config import AntiAIConfig
from src.services.anti_ai.models import (
    DEFAULT_SEVERITY,
    AICategory,
    Severity,
    ViolationSpan,
)


class BaseRuleDetector(ABC):
    """Base class for a single-category rule-based detector.

    Subclasses MUST set :attr:`category` and implement
    :meth:`detect`. The :meth:`_make_violation` helper is provided
    so subclasses do not have to repeat the boilerplate of building
    a :class:`ViolationSpan`.
    """

    #: Which category this detector handles. Set by subclasses.
    category: AICategory

    def __init__(self, config: AntiAIConfig | None = None) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @abstractmethod
    def detect(self, text: str) -> list[ViolationSpan]:
        """Return every violation of this category in ``text``.

        The list may be empty. Order of violations MUST follow
        their appearance in the source text (lowest ``start`` first).
        """

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------
    def _make_violation(
        self,
        start: int,
        end: int,
        matched_text: str,
        severity: Severity | None = None,
        suggestion: str | None = None,
    ) -> ViolationSpan:
        """Convenience constructor for a single ViolationSpan.

        ``severity`` defaults to the per-category default severity
        in :data:`DEFAULT_SEVERITY` so most detectors can omit it.
        """
        return ViolationSpan(
            category=self.category,
            start=start,
            end=end,
            matched_text=matched_text,
            severity=severity or DEFAULT_SEVERITY[self.category],
            suggestion=suggestion,
        )

    def _is_enabled(self) -> bool:
        """Return True if this detector is enabled in the config.

        Returns ``True`` when no config is supplied so the detector
        is usable in unit tests without a config object.
        """
        if self.config is None:
            return True
        try:
            settings = getattr(self.config.detectors, self.category.value)
        except AttributeError:
            return True
        return bool(getattr(settings, "enabled", True))

    # ------------------------------------------------------------------
    # Scoring helper shared by every detector
    # ------------------------------------------------------------------
    def score_from_violations(
        self,
        text: str,
        violations: list[ViolationSpan],
    ) -> float:
        """Translate a list of violations into a 0-100 score.

        Default policy: linearly degrade from 100.0 down to a floor
        based on the density (count per 1000 characters). Detectors
        are free to override this for category-specific scoring
        (e.g. paragraph uniformity needs a different shape than
        simple density).
        """
        if not text:
            return 100.0
        if not violations:
            return 100.0

        density = (len(violations) * 1000) / max(len(text), 1)
        # 0 violations  -> 100
        # 1 per 1000    -> 85
        # 5 per 1000    -> 25
        # >=10 per 1000 -> 0
        penalty = min(100.0, density * 15.0)
        return max(0.0, 100.0 - penalty)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<{type(self).__name__} category={self.category.value!r}>"


__all__ = ["BaseRuleDetector"]
