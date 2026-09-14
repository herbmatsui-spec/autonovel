"""PDCA Writing Directive Engine (Phase 4 / Part 4).

Transforms audit evaluation results and Actionable Diffs into precise,
mandatory rewriting directives for targeted chapter/scene regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from src.agents.specialist_auditor_base import ActionableDiff


@dataclass
class WritingDirective:
    """Represents a mandatory writing constraint/instruction for chapter regeneration."""
    dimension: str  # e.g., "structure", "consistency", "emotion_curve"
    severity: str  # "CRITICAL", "MAJOR", "MINOR"
    target_location: str  # e.g., "起（導入部）", "中盤セグメント"
    current_issue: str  # Problem description or original quote
    mandatory_instruction: str  # Explicit command for writer prompt
    rationale: str  # Reason for the constraint
    specialist_name: str = ""
    foreshadowing_directives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "severity": self.severity,
            "target_location": self.target_location,
            "current_issue": self.current_issue,
            "mandatory_instruction": self.mandatory_instruction,
            "rationale": self.rationale,
            "specialist_name": self.specialist_name,
            "foreshadowing_directives": self.foreshadowing_directives,
        }

    def format_for_prompt(self) -> str:
        """Format directive as a prompt section for chapter generation."""
        sev_marker = {"CRITICAL": "【最優先必須修正】", "MAJOR": "【重点改善要求】", "MINOR": "【表現ブラッシュアップ】"}.get(
            self.severity, "【修正指示】"
        )
        result = (
            f"{sev_marker} 対象箇所: {self.target_location}\n"
            f"  - 現状の課題: {self.current_issue}\n"
        )
        if self.foreshadowing_directives:
            result += f"  - 伏線指示: {', '.join(self.foreshadowing_directives)}\n"
        result += (
            f"  - 必須執筆要件: {self.mandatory_instruction}\n"
            f"  - 改善の狙い: {self.rationale}"
        )
        return result


@dataclass
class PDCACycleResult:
    """Encapsulates the outcome of a closed-loop PDCA regeneration cycle."""
    cycle_number: int
    initial_score: float
    final_score: float
    score_delta: float
    improved_percentage: float
    lowest_dimension: str
    directives_applied: list[WritingDirective] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    converged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_number": self.cycle_number,
            "initial_score": round(self.initial_score, 2),
            "final_score": round(self.final_score, 2),
            "score_delta": round(self.score_delta, 2),
            "improved_percentage": round(self.improved_percentage, 2),
            "lowest_dimension": self.lowest_dimension,
            "directives_count": len(self.directives_applied),
            "directives": [d.to_dict() for d in self.directives_applied],
            "converged": self.converged,
            "history": self.history,
        }


# Dimension-specific prompt templates providing structural guidance (Step 40)
DIMENSION_PROMPT_TEMPLATES: dict[str, str] = {
    "structure": (
        "【構成・ペース配分の特別執筆指針】\n"
        "起承転結のバランスを意識し、不必要な停滞を削ぎ落としてテンポよく展開を進めてください。"
        "特に導入で世界観と目的を明確にし、中盤で葛藤を深め、山場へ加速させてください。"
    ),
    "consistency": (
        "【論理・設定整合性の特別執筆指針】\n"
        "World Bibleのキャラクター生死状態、能力上限、物理的時間軸・距離の整合性を厳密に守ってください。"
        "前後の辻褄が合わない行動や瞬間移動は一切行わないでください。"
    ),
    "reader_hook": (
        "【読者牽引力・フックの特別執筆指針】\n"
        "冒頭第1文・第1段落で読者の心拍数を上げる強烈な謎・危機・異常事態を提示し、"
        "章末には次章を読まずにいられなくなるクリフハンガーを配置してください。"
    ),
    "emotion_curve": (
        "【感情曲線・カタルシスの特別執筆指針】\n"
        "キャラクターの生理的身体反応（呼吸、心拍、汗、手の震え）を描写して感情の落差（振幅）を広げ、"
        "結末部では困難を乗り越えた納得感と深い情動の解放（カタルシス）を描いてください。"
    ),
    "style": (
        "【文体DNA・トーン統一の特別執筆指針】\n"
        "常体（だ・である）または敬体（です・ます）の語尾を完全に統一し、"
        "一人称視点のブレを排除して、世界観に即した格調ある文体を維持してください。"
    ),
    "factual": (
        "【世界観ディテールの特別執筆指針】\n"
        "作中の舞台設定、魔法体系、組織・道具のディテールを正確に描写し、"
        "ふわっとした曖昧な記述を避けて解像度の高い情景を描いてください。"
    ),
    "creativity": (
        "【独創性・新奇性の特別執筆指針】\n"
        "手垢のついたクリシェ表現を避け、鮮烈で意表を突く独自の比喩や意外性のある展開を組み込んでください。"
    ),
    "multimodal": (
        "【情景・五感調和の特別執筆指針】\n"
        "視覚（光・影・色彩）、聴覚（環境音・囁き）、嗅覚、触覚を組み合わせた立体的な描写を行ってください。"
    ),
}


class PDCADirectiveGenerator:
    """Generates targeted writing directives from audit results and Actionable Diffs."""

    SEVERITY_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}

    @staticmethod
    def identify_target_dimensions(
        scores: Mapping[str, float],
        target_threshold: float = 75.0,
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        """Identify dimensions below target threshold in ascending order (Step 38)."""
        below = [(dim, float(sc)) for dim, sc in scores.items() if sc < target_threshold]
        below.sort(key=lambda x: x[1])
        if not below and scores:
            # If all are above threshold, pick the lowest top_k
            all_sorted = sorted(scores.items(), key=lambda x: x[1])
            return all_sorted[:top_k]
        return below[:top_k]

    @classmethod
    def diff_to_directive(
        cls,
        diff: ActionableDiff,
        dimension: str,
        dimension_score: float,
        specialist_name: str = "",
    ) -> WritingDirective:
        """Convert a specialist Actionable Diff into a WritingDirective (Step 39)."""
        # Determine severity based on score and content
        if dimension_score < 50.0:
            severity = "CRITICAL"
        elif dimension_score < 70.0:
            severity = "MAJOR"
        else:
            severity = "MINOR"

        loc = diff.location or "該当箇所"
        quote = diff.original_quote or "（問題のある既存描写）"
        suggestion = diff.improved_suggestion or "表現の修正・拡充"
        rationale = diff.rationale or "評価スコア向上のため"

        instruction = (
            f"原文抜粋『{quote}』の描写を改め、"
            f"以下の指示通りにリライトすること: {suggestion}"
        )
        # Check if this diff is related to foreshadowing
        is_foreshadowing_related = (
            "伏線" in loc or "伏線" in quote or "伏線" in suggestion or "伏線" in rationale
        )
        foreshadowing_directives = []
        if is_foreshadowing_related:
            # For now, we can add a generic foreshadowing directive
            foreshadowing_directives.append("伏線の描写を適切に反映させ、物語の整合性を保つようにしてください。")
        return WritingDirective(
            dimension=dimension,
            severity=severity,
            target_location=loc,
            current_issue=quote,
            mandatory_instruction=instruction,
            rationale=rationale,
            specialist_name=specialist_name or dimension,
            foreshadowing_directives=foreshadowing_directives,
        )

    @classmethod
    def generate_directives_for_regeneration(
        cls,
        scores_by_specialist: Mapping[str, float],
        actionable_diffs: Sequence[ActionableDiff],
        target_threshold: float = 75.0,
        max_directives: int = 5,
    ) -> list[WritingDirective]:
        """Generate, prioritize, and sort writing directives for chapter rewrite (Step 41)."""
        target_dims = dict(cls.identify_target_dimensions(scores_by_specialist, target_threshold=target_threshold))
        directives: list[WritingDirective] = []

        # 1. Convert relevant Actionable Diffs
        for diff in actionable_diffs:
            # Map diff to matched dimension if possible
            matched_dim = "general"
            matched_score = 65.0
            for dim, score in target_dims.items():
                if dim in diff.location.lower() or dim in getattr(diff, "specialist_name", "").lower():
                    matched_dim = dim
                    matched_score = score
                    break
            if matched_dim == "general" and target_dims:
                # Assign to lowest scoring dimension
                matched_dim, matched_score = next(iter(target_dims.items()))

            directive = cls.diff_to_directive(diff, matched_dim, matched_score)
            directives.append(directive)

        # 2. If diffs are fewer than target dimensions, add synthetic directives from templates
        for dim, score in target_dims.items():
            has_diff = any(d.dimension == dim for d in directives)
            if not has_diff and dim in DIMENSION_PROMPT_TEMPLATES:
                sev = "CRITICAL" if score < 50.0 else ("MAJOR" if score < 70.0 else "MINOR")
                directives.append(
                    WritingDirective(
                        dimension=dim,
                        severity=sev,
                        target_location=f"{dim} 全体",
                        current_issue=f"スコアが目標値（{target_threshold}点）を下回っています（現在{score:.1f}点）。",
                        mandatory_instruction=DIMENSION_PROMPT_TEMPLATES[dim],
                        rationale=f"{dim}の底上げによる小説全体の商業的完成度向上。",
                        specialist_name=dim,
                    )
                )

        # 3. Sort by severity and limit count
        directives.sort(key=lambda d: (cls.SEVERITY_ORDER.get(d.severity, 2), -len(d.mandatory_instruction)))
        return directives[:max_directives]

    @classmethod
    def format_directives_for_llm_prompt(
        cls,
        directives: list[WritingDirective],
        header: str = "【閉ループPDCA・再生成必須制約（必ず遵守すること）】",
    ) -> str:
        """Format the list of directives into a single prompt block for the writer LLM."""
        if not directives:
            return ""

        lines = [header, "前回の評価で基準点に満たなかった弱点を克服するため、以下の項目を必ず反映して再執筆してください:\n"]
        for i, d in enumerate(directives, 1):
            lines.append(f"《修正指示 {i}》")
            lines.append(d.format_for_prompt())
            lines.append("")

        return "\n".join(lines)


__all__ = [
    "WritingDirective",
    "PDCACycleResult",
    "PDCADirectiveGenerator",
    "DIMENSION_PROMPT_TEMPLATES",
]