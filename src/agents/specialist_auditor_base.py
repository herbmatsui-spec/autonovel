"""Specialist Auditor base class.

Phase 2 / Guideline #3: 8 specialist auditors share this interface.
Each specialist receives an AgentContext-like dict and returns a
SpecialistAuditResult with a 0-100 score, feedback dict and suggestions.
LLM-using specialists may raise LLMUnavailableError to fall back to the
rule-based path; the aggregator captures this and records a missing status.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMUnavailableError(RuntimeError):
    """Raised by an LLM-using specialist when the LLM is down. The
    aggregator will catch this and fall back to the rule-based path of
    the same specialist.
    """


@dataclass
class SpecialistAuditResult:
    specialist_name: str
    score: float  # 0-100
    feedback: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    degraded: bool = False  # True if fell back to rule-based path
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist_name": self.specialist_name,
            "score": self.score,
            "feedback": self.feedback,
            "suggestions": list(self.suggestions),
            "degraded": self.degraded,
            "error": self.error,
        }


class SpecialistAuditor(ABC):
    """Abstract base for all 8 specialist auditors.

    Subclasses MUST define ``specialist_name`` (one of:
    consistency / creativity / reader_hook / emotion_curve / style /
    factual / structure / multimodal) and implement ``audit``.
    """

    specialist_name: str = ""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    @abstractmethod
    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Run audit on the context. MUST be async and MUST return a
        SpecialistAuditResult with score in [0, 100].
        """

    async def _safe_audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        try:
            return await self.audit(ctx)
        except LLMUnavailableError as e:
            fb = self._fallback(ctx)
            fb.degraded = True
            fb.error = f"llm_unavailable: {e}"
            return fb
        except Exception as e:
            return SpecialistAuditResult(
                specialist_name=self.specialist_name,
                score=0.0,
                feedback={"exception": str(e)},
                suggestions=[],
                degraded=True,
                error=repr(e),
            )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback used when LLM is unavailable.
        Default: return a neutral 50 score. Specialists override this
        to provide meaningful rule-based scoring.
        """
        return SpecialistAuditResult(
            specialist_name=self.specialist_name,
            score=50.0,
            feedback={"fallback": "rule-based default"},
            suggestions=["LLM unavailable; consider manual review"],
            degraded=True,
        )


__all__ = [
    "SpecialistAuditor",
    "SpecialistAuditResult",
    "LLMUnavailableError",
]