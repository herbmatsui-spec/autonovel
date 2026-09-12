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
    ActionableDiff,
)
from src.agents.specialists.fallback_utils import (
    analyze_pacing,
)

STRUCTURE_SYSTEM_PROMPT = """あなたは小説の構成・プロット展開・起承転結（Structure & Pacing）を審査する専門オーディターです。
以下の観点で文章の構成とペース配分を厳格に評価してください:
1. プロット目標の消化と論理的展開: 与えられたプロット要素（伏線・事件・解決）が無理なく消化・進展しているか。
2. 起承転結または三幕構成のバランス: 導入・展開・転換・結びの配分が適切か（冗長な停滞や唐突すぎる飛躍がないか）。
3. シーンのテンポとペース配分（Pacing）: 読者が飽きないリズム感が維持されているか。
構成が破綻している、プロットが未消化のまま放置されている場合は低スコア（50点未満）、完成度が高く引き締まった構成であれば高スコア（80点以上）としてください。

【Actionable Diff の必須出力要件】
起承転結の各セクション（特に起・承・転・結のいずれかで停滞や唐突感がある箇所）について、
必ず「問題のある原文の抜粋」と「改善後の具体的な構成リライト案」を1〜3件 ActionableDiff に含めてください。
"""

STRUCTURE_USER_PROMPT = """【プロットツリー / 予定展開】
{plot_tree}

【執筆ドラフト本文】
{draft_text}

上記文章がプロットの要件を正しく満たし、起承転結・ペース配分が適切であるかを審査し、0〜100で採点してください。
起承転結の改善が必要な箇所について、具体的な Actionable Diff を必ず出力してください。
"""

STRUCTURE_WINDOWED_USER_PROMPT = """【プロットツリー / 予定展開】
{plot_tree}

【総文字数】{total_chars}文字
【起（導入セクション）】
{ki_text}

【承（展開セクション）】
{sho_text}

【転（山場・転換セクション）】
{ten_text}

【結（結び・余韻セクション）】
{ketsu_text}

上記文章がプロットの要件を正しく満たし、起承転結の配分および展開のテンポ・ペース配分が適切であるかを審査し、0〜100で採点してください。
起・承・転・結のバランスや展開速度の改善が必要な箇所について、具体的な Actionable Diff を必ず出力してください。
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
        sections = self.section_extractor.extract_four_sections(draft, section_chars=800)
        sec_dict = {s.name: s.text for s in sections}

        prompt = STRUCTURE_WINDOWED_USER_PROMPT.format(
            plot_tree=plot_info[:2000],
            total_chars=len(draft),
            ki_text=sec_dict.get("ki", ""),
            sho_text=sec_dict.get("sho", ""),
            ten_text=sec_dict.get("ten", ""),
            ketsu_text=sec_dict.get("ketsu", ""),
        )

        judge_res = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
        )
        score, critique, suggestions, confidence, reasoning, raw_resp = judge_res[:6]
        actionable_diffs = judge_res[6] if len(judge_res) > 6 else []

        return SpecialistAuditResult(
            specialist_name="structure",
            score=score,
            feedback={
                "critique": critique,
                "total_chars": len(draft),
                "sections_extracted": {s.name: len(s.text) for s in sections},
            },
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
            actionable_diffs=actionable_diffs,
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
        actionable_diffs: list[ActionableDiff] = []

        phase_labels = {
            "intro": ("起（導入部）", "世界観や主人公の日常・初期状態を描写し、事件の発端への導入を明瞭にする"),
            "conflict": ("承（展開部）", "主人公が直面する試練や葛藤、対立要素を段階的に深める展開を追加する"),
            "climax": ("転（山場・転換部）", "決定的な事件の転換や最大のピンチ・驚きの展開を際立たせる"),
            "resolution": ("結（結末・余韻）", "事件の決着と主人公の内面的変化、次章へのフックを丁寧に描く"),
        }

        for phase, cov in phase_scores.items():
            if cov < 0.5:
                label, suggestion_text = phase_labels.get(phase, (phase, "プロット要素の補強"))
                suggestions.append(f"{label}のプロット消化・展開を補強してください")
                # 原文抜粋の切り出し（テキスト長に応じた抜粋）
                quote = draft[:60] if phase in ["intro", "conflict"] else draft[-60:]
                actionable_diffs.append(
                    ActionableDiff(
                        location=label,
                        original_quote=quote.strip() or "（該当セクションの記述不足）",
                        improved_suggestion=f"{suggestion_text}。",
                        rationale=f"{label}におけるプロットキーワード消化率が低く（{int(cov * 100)}%）、構成上の厚みが不足しているため。",
                    )
                )

        if avg_coverage < 0.5 and not suggestions:
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
            actionable_diffs=actionable_diffs,
        )


__all__ = ["StructureAuditor"]