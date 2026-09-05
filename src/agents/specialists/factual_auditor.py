"""Factual Specialist Auditor (Step 64).

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

FACTUAL_SYSTEM_PROMPT = """あなたは歴史考証・文化設定・世界観事実整合性（Factual Accuracy）を審査する専門オーディターです。
与えられた「World Bible設定」と「本文」を照合し、以下の観点を評価してください:
1. 世界観用語・固有名詞の誤用や混同
2. 中世ファンタジー等の時代設定にそぐわない現代語・文明利器の無自覚な混入（アクロニズム）
3. 地理・組織・階級秩序の事実関係の逸脱
"""

FACTUAL_USER_PROMPT = """【World Bible 設定】
{world_bible}

【執筆本文】
{draft_text}

設定用語・事実関係・時代考証の整合性を評価し、0〜100で採点してください。
重大な事実誤認や設定違反がある場合は低スコア（50点未満）としてください。
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
            raise LLMUnavailableError("No LLM available for FactualAuditor")

        bible_summary = self._summarize_bible(bible)
        prompt = FACTUAL_USER_PROMPT.format(
            world_bible=bible_summary or "特になし",
            draft_text=draft[:4000],
        )

        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=FACTUAL_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="factual",
            score=score,
            feedback={
                "critique": critique,
                "bible_summary": bible_summary[:200] if bible_summary else "",
            },
            suggestions=suggestions,
            degraded=False,
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
        """Rule-based fallback for factual auditor (modern terms + entity coverage)."""
        draft = ctx.get("draft_text", "") or ""
        bible = ctx.get("world_bible_snapshot") or {}
        if not draft:
            return SpecialistAuditResult("factual", 0.0, feedback={"error": "no draft"}, degraded=True)

        modern_words = ["スマホ", "インターネット", "電車", "コンビニ", "エレベーター", "コンクリート"]
        found_modern = [w for w in modern_words if w in draft]

        ref_entities = set()
        for key in ("characters", "locations", "items", "factions", "terms"):
            val = bible.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        ref_entities.add(item.get("name", ""))
                    elif isinstance(item, str):
                        ref_entities.add(item)

        coverage = sum(1 for e in ref_entities if e in draft) / len(ref_entities) if ref_entities else 0.8
        score = max(20.0, min(100.0, coverage * 70.0 + 30.0 - len(found_modern) * 25.0))

        return SpecialistAuditResult(
            specialist_name="factual",
            score=round(score, 1),
            feedback={
                "fallback": "rule-based",
                "modern_terms_found": found_modern,
                "coverage": round(coverage, 2),
            },
            suggestions=[f"Remove modern term: {w}" for w in found_modern],
            degraded=True,
        )


__all__ = ["FactualAuditor"]