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
from src.agents.specialists.fallback_utils import (
    analyze_pacing,
    compute_coverage,
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

        score, critique, suggestions, confidence, reasoning, raw_resp = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="structure",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using plot keyword coverage and pacing analysis."""
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

        # Phase-based keyword coverage
        # Split plot into 4 phases: intro, conflict, climax, resolution
        plot_phases = ["導入", "展開", "転換", "結び", "起", "承", "転", "結", "intro", "conflict", "climax", "resolution"]
        phase_keywords = {phase: [] for phase in ["intro", "conflict", "climax", "resolution"]}

        # Simple heuristic: split plot by common delimiters
        plot_parts = re.split(r"[→→、。,\n・]+", str(plot))
        plot_parts = [p.strip() for p in plot_parts if p.strip()]

        # Distribute keywords across 4 phases
        for i, part in enumerate(plot_parts):
            phase_idx = min(i, 3)
            phase_name = ["intro", "conflict", "climax", "resolution"][phase_idx]
            keywords = [w for w in re.split(r"[、。,\s\n・]+", part) if len(w) > 1]
            phase_keywords[phase_name].extend(keywords)

        # Compute coverage per phase
        phase_scores = {}
        for phase, keywords in phase_keywords.items():
            if keywords:
                found = sum(1 for k in keywords if k in draft)
                phase_scores[phase] = found / len(keywords)
            else:
                phase_scores[phase] = 0.5  # neutral if no keywords

        avg_coverage = sum(phase_scores.values()) / 4 if phase_scores else 0.5

        # Pacing analysis - only meaningful for longer texts
        if len(draft) > 200:
            pacing_score = analyze_pacing(draft, ["intro", "conflict", "climax", "resolution"])
            pacing_weight = 0.3
        else:
            pacing_score = 0.5
            pacing_weight = 0.1

        # Combined score: coverage weight + pacing weight
        coverage_weight = 1.0 - pacing_weight
        score = max(20.0, min(100.0, round((coverage_weight * avg_coverage + pacing_weight * pacing_score) * 100.0, 1)))

        suggestions = []
        if avg_coverage < 0.5:
            suggestions.append("Cover more plot points across all phases")
        if pacing_score < 0.4 and len(draft) > 200:
            suggestions.append("Improve pacing balance between phases")
        if not suggestions:
            suggestions = ["Structure looks good"]

        return SpecialistAuditResult(
            "structure",
            score,
            feedback={
                "fallback": "rule-based phase coverage + pacing",
                "phase_coverage": {k: round(v, 3) for k, v in phase_scores.items()},
                "avg_coverage": round(avg_coverage, 3),
                "pacing_score": round(pacing_score, 3),
            },
            suggestions=suggestions,
            degraded=True,
        )


__all__ = ["StructureAuditor"]