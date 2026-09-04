"""Structure Specialist Auditor.

Phase 2 / Guideline #3-⑦: Chapter structure, plot tree logical flow, pacing,
Kishotenketsu appropriateness. LLM-based with rule-based fallback.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)


STRUCTURE_PROMPT = """以下の本文が、与えられたプロットツリーのどのノードを消化したか判定してください。

【プロットツリー（簡易）】
{plot_tree}

【本文】
{draft_text}

以下をJSONで回答:
{
  "digested_nodes": ["ノードID", ...],
  "undigested_nodes": ["ノードID", ...],
  "summary": "全体の構造判定"
}
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

        if self.llm is None:
            raise LLMUnavailableError("No LLM available")

        prompt = STRUCTURE_PROMPT.format(
            plot_tree=str(plot_tree)[:2000],
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
            digested = data.get("digested_nodes", [])
            undigested = data.get("undigested_nodes", [])
            summary = data.get("summary", "")
        except Exception:
            digested, undigested, summary = [], [], "parse failed"

        total_nodes = len(digested) + len(undigested)
        if total_nodes == 0:
            score = 50.0
        else:
            score = (len(digested) / total_nodes) * 100.0

        return SpecialistAuditResult(
            "structure",
            round(score, 1),
            feedback={
                "digested_nodes": digested,
                "undigested_nodes": undigested,
                "summary": summary,
                "digested_count": len(digested),
                "total_nodes": total_nodes,
            },
            suggestions=[
                f"Address undigested node: {n}" for n in undigested[:3]
            ] if undigested else [],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        # Rule-based: check if plot keywords appear in draft
        draft = ctx.get("draft_text", "") or ""
        plot = ctx.get("plot_tree") or ctx.get("plot_summary") or ""
        if not plot:
            return SpecialistAuditResult(
                "structure", 50.0,
                feedback={"fallback": "no plot tree", "degraded": True},
                suggestions=["Provide plot tree for structure check"],
                degraded=True,
            )
        # Extract potential plot nodes (split on punctuation and common separators)
        import re
        plot_keywords = [w for w in re.split(r"[、。,\s\n・]+", plot) if len(w) > 1]
        if not plot_keywords:
            return SpecialistAuditResult("structure", 50.0, feedback={"fallback": "no keywords"}, degraded=True)
        found = sum(1 for k in plot_keywords if k in draft)
        coverage = found / len(plot_keywords)
        score = coverage * 100.0
        return SpecialistAuditResult(
            "structure",
            round(score, 1),
            feedback={
                "fallback": "rule-based keyword coverage",
                "plot_keywords": len(plot_keywords),
                "found_in_draft": found,
                "coverage": round(coverage, 3),
            },
            degraded=True,
            suggestions=["Cover more plot points"] if coverage < 0.5 else [],
        )


__all__ = ["StructureAuditor"]