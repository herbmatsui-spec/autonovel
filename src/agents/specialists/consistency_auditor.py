"""Consistency Specialist Auditor.

Phase 2 / Guideline #3-①: Character behavior, world rules, timeline logical consistency.
Pure rule-based (LLM-free). Cross-references proper nouns against World Bible snapshot.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult


class ConsistencyAuditor(SpecialistAuditor):
    specialist_name = "consistency"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        bible = ctx.get("world_bible_snapshot") or {}
        if not draft:
            return SpecialistAuditResult(
                "consistency", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        # Build reference set from bible
        ref_nouns: set[str] = set()
        for key in ("characters", "locations", "items", "factions", "terms"):
            val = bible.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        name = item.get("name", "")
                        if name:
                            ref_nouns.add(name)
                    elif isinstance(item, str):
                        ref_nouns.add(item)
            elif isinstance(val, dict):
                name = val.get("name", "")
                if name:
                    ref_nouns.add(name)

        if not ref_nouns:
            return SpecialistAuditResult(
                "consistency", 50.0,
                feedback={"bible_entities": 0},
                suggestions=["Populate World Bible for consistency checks"],
            )

        # Count how many reference nouns appear in draft
        found = sum(1 for n in ref_nouns if n in draft)
        total = len(ref_nouns)
        coverage = found / total if total else 0.0

        # Contradiction heuristic: noun near both death and life words
        contradiction_penalty = 0.0
        for noun in ref_nouns:
            idx = draft.find(noun)
            if idx >= 0:
                window = draft[max(0, idx - 40):idx + 40]
                if ("死" in window or "死亡" in window) and ("生" in window or "生きて" in window):
                    contradiction_penalty += 0.15

        score = max(0.0, min(100.0, (coverage * 0.85 - contradiction_penalty * 0.15) * 100.0))

        return SpecialistAuditResult(
            "consistency",
            round(score, 1),
            feedback={
                "bible_entities_total": total,
                "bible_entities_found": found,
                "coverage_rate": round(coverage, 3),
                "contradiction_penalty": round(contradiction_penalty, 3),
            },
            suggestions=["Update World Bible with missing names"] if found < total else [],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self.audit(ctx)


__all__ = ["ConsistencyAuditor"]