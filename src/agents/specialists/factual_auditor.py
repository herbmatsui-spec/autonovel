"""Factual Specialist Auditor.

Phase 2 / Guideline #3-⑥: GraphRAG reference consistency, historical/cultural
accuracy, terminology appropriateness. LLM-based with rule-based fallback.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)


FACTUAL_PROMPT = """以下の本文が、与えられた世界観設定と矛盾していないか確認してください。

【世界観設定】
{world_bible}

【本文】
{draft_text}

矛盾する箇所があれば、具体的に「エンティティ名: 矛盾内容」の形式で列挙してください。
矛盾がなければ「矛盾なし」と答えてください。

出力形式（JSON）:
{{"contradictions": ["エンティティ: 内容", ...], "summary": "全体の判定"}}
"""


class FactualAuditor(SpecialistAuditor):
    specialist_name = "factual"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        bible = ctx.get("world_bible_snapshot") or {}
        if not draft:
            return SpecialistAuditResult(
                "factual", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if self.llm is None:
            raise LLMUnavailableError("No LLM available")

        bible_summary = self._summarize_bible(bible)

        prompt = FACTUAL_PROMPT.format(
            world_bible=bible_summary,
            draft_text=draft[:3000],
        )

        try:
            response = await self.llm.agenerate([prompt])
            text = response.generations[0][0].text
        except Exception as e:
            raise LLMUnavailableError(f"LLM call failed: {e}") from e

        import json
        try:
            data = json.loads(text)
            contradictions = data.get("contradictions", [])
            summary = data.get("summary", "")
        except Exception:
            contradictions = [line.strip() for line in text.split("\n") if ":" in line]
            summary = "parsed from text"

        num_contradictions = len(contradictions)
        score = max(0.0, 100.0 - num_contradictions * 15.0)

        return SpecialistAuditResult(
            "factual",
            round(score, 1),
            feedback={
                "contradictions": contradictions[:10],
                "summary": summary,
                "contradiction_count": num_contradictions,
            },
            suggestions=[
                f"Fix contradiction: {c}" for c in contradictions[:3]
            ] if contradictions else [],
        )

    def _summarize_bible(self, bible: dict) -> str:
        parts = []
        for key in ("characters", "locations", "items", "factions", "terms", "rules"):
            val = bible.get(key)
            if isinstance(val, list) and val:
                names = []
                for item in val[:10]:
                    if isinstance(item, dict):
                        names.append(item.get("name", str(item)))
                    else:
                        names.append(str(item))
                parts.append(f"{key}: {', '.join(names)}")
            elif isinstance(val, dict) and val.get("name"):
                parts.append(f"{key}: {val['name']}")
        return "\n".join(parts) if parts else "（設定なし）"

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        bible = ctx.get("world_bible_snapshot") or {}
        ref_entities = set()
        for key in ("characters", "locations", "items", "factions", "terms"):
            val = bible.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        ref_entities.add(item.get("name", ""))
                    elif isinstance(item, str):
                        ref_entities.add(item)
        if not ref_entities:
            return SpecialistAuditResult(
                "factual", 50.0,
                feedback={"fallback": "no bible entities", "bible_entities": 0},
                suggestions=["Populate World Bible for factual checks"],
            )
        found = sum(1 for e in ref_entities if e in draft)
        coverage = found / len(ref_entities)
        score = coverage * 100.0
        return SpecialistAuditResult(
            "factual",
            round(score, 1),
            feedback={
                "fallback": "rule-based entity coverage",
                "bible_entities": len(ref_entities),
                "found_in_draft": found,
                "coverage": round(coverage, 3),
            },
            degraded=True,
            suggestions=["Add missing entities to draft"] if found < len(ref_entities) else [],
        )


__all__ = ["FactualAuditor"]