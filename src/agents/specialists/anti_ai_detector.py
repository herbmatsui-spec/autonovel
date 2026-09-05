"""Anti-AI Detection Specialist Auditor.

Phase 5 / Steps 49-55: Specialist auditor that detects AI-generated
prose fingerprints using rule-based detection and optional LLM verification.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult
from src.services.anti_ai.orchestrator import RuleBasedAntiAIDetector
from src.services.anti_ai.models import AICategory


class AntiAIDetector(SpecialistAuditor):
    specialist_name = "anti_ai"

    def __init__(
        self,
        llm: Any = None,
        enable_llm_check: bool = False,
    ) -> None:
        super().__init__(llm)
        self._detector = RuleBasedAntiAIDetector()
        self._enable_llm_check = enable_llm_check

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "anti_ai",
                0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        result = self._detector.detect(draft)
        score = result.total_score

        suggestions = []
        for category, cat_score in result.category_scores.items():
            if cat_score < 70:
                suggestions.append(f"Improve {category.value} score ({cat_score:.1f})")

        return SpecialistAuditResult(
            "anti_ai",
            round(score, 1),
            feedback={
                "category_scores": {k.value: v for k, v in result.category_scores.items()},
                "total_violations": len(result.violations),
                "total_score": result.total_score,
            },
            suggestions=suggestions if suggestions else ["Scores are good"],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self._sync_audit(ctx)

    def _sync_audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "anti_ai",
                0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        result = self._detector.detect(draft)
        score = result.total_score

        suggestions = []
        for category, cat_score in result.category_scores.items():
            if cat_score < 70:
                suggestions.append(f"Improve {category.value} score ({cat_score:.1f})")

        return SpecialistAuditResult(
            "anti_ai",
            round(score, 1),
            feedback={
                "category_scores": {k.value: v for k, v in result.category_scores.items()},
                "total_violations": len(result.violations),
                "total_score": result.total_score,
            },
            suggestions=suggestions if suggestions else ["Scores are good"],
            degraded=True,
        )


__all__ = ["AntiAIDetector"]
