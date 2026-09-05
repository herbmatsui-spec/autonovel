"""Structure Specialist Auditor.

Phase 2 / Guideline #3-⑦: Chapter structure, plot tree logical flow, pacing,
Kishotenketsu appropriateness. Evaluated via LLM reasoning with rule-based fallback.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)

STRUCTURE_SYSTEM_PROMPT = """あなたは小説の構成・プロット展開・起承転結（Structure & Pacing）を審査する専門オーディターです。
以下の観点で文章の構成とペース配分を厳格に評価してください:
1. プロット目標の消化と論理的展開: 与えられたプロット要素（伏線・事件・解決）が無理なく消化・進展しているか。
2. 起承転結または三幕構成のバランス: 導入・展開・転換・結びの配分が適切か（冗長な停滞や唐突すぎる飛躍がないか）。
3. シーンのテンポとペース配分（Pacing）: 読者が飽きないリズム感が維持されているか。
構成が破綻している、プロットが未消化のまま放置されている場合は低スコア（50点未満）、完成度が高く引き締まった構成であれば高スコア（80点以上）としてください。
"""

STRUCTURE_USER_PROMPT = """【プロットツリー / 予定展開】
{plot_tree}

【執筆ドラフト本文】
{draft_text}

上記文章がプロットの要件を正しく満たし、起承転結・ペース配分が適切であるかを審査し、0〜100で採点してください。
"""


class StructureAuditor(SpecialistAuditor):
    specialist_name = "structure"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        plot_tree = ctx.get("plot_tree") or ctx.get("plot_summary") or ""
        if not draft:
            return SpecialistAuditResult(
                "structure", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if not self.llm:
            raise LLMUnavailableError("No LLM available for StructureAuditor")

        plot_info = str(plot_tree) if plot_tree else "標準起承転結プロット（導入→危機・葛藤→解決・余韻）"
        prompt = STRUCTURE_USER_PROMPT.format(
            plot_tree=plot_info[:2000],
            draft_text=draft[:4000],
        )

        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="structure",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using plot keyword coverage in draft."""
        draft = ctx.get("draft_text", "") or ""
        plot = ctx.get("plot_tree") or ctx.get("plot_summary") or ""
        if not draft:
            return SpecialistAuditResult("structure", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        if not plot:
            return SpecialistAuditResult(
                "structure", 50.0,
                feedback={"fallback": "no plot tree", "degraded": True},
                suggestions=["Provide plot tree for structure check"],
                degraded=True,
            )

        plot_keywords = [w for w in re.split(r"[、。,\s\n・]+", str(plot)) if len(w) > 1]
        if not plot_keywords:
            return SpecialistAuditResult("structure", 50.0, feedback={"fallback": "no keywords"}, degraded=True)

        found = sum(1 for k in plot_keywords if k in draft)
        coverage = found / len(plot_keywords)
        score = max(20.0, min(100.0, round(coverage * 80.0 + 20.0, 1)))

        return SpecialistAuditResult(
            "structure",
            score,
            feedback={
                "fallback": "rule-based keyword coverage",
                "plot_keywords": len(plot_keywords),
                "found_in_draft": found,
                "coverage": round(coverage, 3),
            },
            suggestions=["Cover more plot points"] if coverage < 0.5 else [],
            degraded=True,
        )


__all__ = ["StructureAuditor"]