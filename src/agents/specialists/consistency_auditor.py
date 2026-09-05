"""Consistency Specialist Auditor (Step 64).

Phase 2 / Guideline #3-①: Character behavior, world rules, timeline logical consistency.
Uses LLM-based logical inference to detect plot contradictions, deceased character reappearance,
and world rule violations, with graceful rule-based fallback.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)

CONSISTENCY_SYSTEM_PROMPT = """あなたは小説の設定・論理一貫性（Consistency）を厳格に審査する専門編集オーディターです。
与えられた「World Bible設定」と「執筆ドラフト本文」を照合し、以下の観点で論理矛盾を精査してください:
1. キャラクターの生死・負傷・能力制限の整合性（死亡したはずの人物の理由なき再登場等）
2. 行動動機と前後の心理・性格DNAの整合性
3. 舞台設定・時間軸（昼夜、距離、経過時間）の物理的・論理的一貫性
4. 世界観の魔法体系・科学ルールの逸脱
"""

CONSISTENCY_USER_PROMPT = """【World Bible 設定】
{bible_summary}

【執筆ドラフト本文】
{draft_text}

上記テキストの論理一貫性を厳格に審査し、矛盾の有無と重大度に基づいて0〜100で採点してください。
明確な設定矛盾（例: 死亡人物の唐突な登場、場所の瞬間移動）がある場合は大幅に減点（40点以下）してください。
"""


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

        if not self.llm:
            raise LLMUnavailableError("No LLM configured for ConsistencyAuditor")

        bible_summary = self._summarize_bible(bible)
        prompt = CONSISTENCY_USER_PROMPT.format(
            bible_summary=bible_summary or "特になし",
            draft_text=draft[:4000],
        )

        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=CONSISTENCY_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="consistency",
            score=score,
            feedback={
                "critique": critique,
                "bible_summary": bible_summary[:200] if bible_summary else "",
            },
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback without death/life window regex heuristic."""
        draft = ctx.get("draft_text", "") or ""
        bible = ctx.get("world_bible_snapshot") or {}
        if not draft:
            return SpecialistAuditResult("consistency", 0.0, feedback={"error": "no draft_text"}, degraded=True)

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

        if not ref_nouns:
            return SpecialistAuditResult("consistency", 60.0, feedback={"coverage": "neutral"}, degraded=True)

        found = sum(1 for n in ref_nouns if n in draft)
        coverage = found / len(ref_nouns) if ref_nouns else 0.5
        score = max(40.0, min(90.0, round(coverage * 80.0 + 20.0, 1)))

        return SpecialistAuditResult(
            specialist_name="consistency",
            score=score,
            feedback={"rule_coverage": round(coverage, 2), "found_entities": found},
            suggestions=["Populate World Bible for more thorough checks"],
            degraded=True,
        )

    def _summarize_bible(self, bible: dict[str, Any]) -> str:
        parts = []
        for key in ("characters", "locations", "items", "factions", "terms", "rules"):
            val = bible.get(key)
            if isinstance(val, list) and val:
                names = []
                for item in val[:8]:
                    if isinstance(item, dict):
                        status = f" (状態:{item['status']})" if "status" in item else ""
                        names.append(f"{item.get('name', '名無し')}{status}")
                    else:
                        names.append(str(item))
                parts.append(f"- {key}: {', '.join(names)}")
            elif isinstance(val, dict) and val:
                parts.append(f"- {key}: {val}")
        return "\n".join(parts)


__all__ = ["ConsistencyAuditor"]