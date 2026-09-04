"""Reader Hook Specialist Auditor.

Phase 2 / Guideline #3-③: Opening hook strength (mystery/discomfort/crisis) and
ending cliffhanger score. Pure rule-based (LLM-free).
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult


# Hook keywords for opening
OPENING_HOOK_PATTERNS = [
    r"なぜ", r"どうして", r"誰", r"何", r"どこ", r"いつ",
    r"謎", r"不思議", r"奇妙", r"違和感", r"おかしい",
    r"危機", r"ピンチ", r"絶体絶命", r"追い詰め", r"逃げ",
    r"突然", r"唐突", r"一瞬", r"瞬間", r"衝撃",
    r"？", r"！", r"…", r"……",
]

# Hook keywords for ending
ENDING_HOOK_PATTERNS = [
    r"…$", r"……$", r"？$", r"！$",
    r"どうなる", r"どうしろ", r"どうする", r"続く", r"次回",
    r"未解決", r"謎のまま", r"分からない", r"わからない",
    r"見えた", r"現れた", r"現れ", r"扉が", r"音が",
]


class ReaderHookAuditor(SpecialistAuditor):
    specialist_name = "reader_hook"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "reader_hook", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        # Examine first 200 chars (opening) and last 200 chars (ending)
        opening = draft[:200]
        ending = draft[-200:] if len(draft) > 200 else draft

        opening_score = self._score_hooks(opening, OPENING_HOOK_PATTERNS, max_score=40)
        ending_score = self._score_hooks(ending, ENDING_HOOK_PATTERNS, max_score=60)

        total = opening_score + ending_score

        return SpecialistAuditResult(
            "reader_hook",
            round(total, 1),
            feedback={
                "opening_chars": len(opening),
                "ending_chars": len(ending),
                "opening_score": round(opening_score, 1),
                "ending_score": round(ending_score, 1),
            },
            suggestions=[
                "Strengthen opening hook with a question or crisis" if opening_score < 20 else None,
                "Add cliffhanger or unresolved question at end" if ending_score < 30 else None,
            ],
        )

    def _score_hooks(self, text: str, patterns: list[str], max_score: float) -> float:
        if not text:
            return 0.0
        hits = sum(1 for p in patterns if re.search(p, text))
        # Diminishing returns: 1st hit = 1.0, 2nd = 0.7, 3rd = 0.5, etc.
        score = 0.0
        for i in range(hits):
            score += max_score * (1.0 / (i + 1)) * 0.4
        return min(max_score, score)

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self.audit(ctx)


__all__ = ["ReaderHookAuditor"]