"""Multimodal Specialist Auditor.

Phase 2 / Guideline #3-⑧: Illustration prompt / text description consistency.
Checks information amount match, focus alignment, emotional tone consistency.
LLM-based with rule-based fallback.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)


MULTIMODAL_PROMPT = """以下の本文と挿絵プロンプトの整合性を判定してください。

【本文（抜粋）】
{draft_text}

【挿絵プロンプト】
{illustration_prompts}

以下の観点で 0.0-1.0 のスコアで評価しJSONで回答:
{
  "information_match": 0.0-1.0,  # 同じシーンを描写しているか
  "focus_match": 0.0-1.0,        # 本文の焦点と挿絵の焦点が一致しているか
  "tone_match": 0.0-1.0,         # 感情トーン（悲しい/楽しい/緊張等）が一致しているか
  "summary": "判定理由"
}
"""


class MultimodalAuditor(SpecialistAuditor):
    specialist_name = "multimodal"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        illust_prompts = ctx.get("illustration_prompts") or ctx.get("illustration_prompt") or ""
        if not draft:
            return SpecialistAuditResult(
                "multimodal", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )
        if not illust_prompts:
            return SpecialistAuditResult(
                "multimodal", 50.0,
                feedback={"note": "no illustration prompts provided"},
                suggestions=["Provide illustration_prompts for multimodal check"],
            )

        if self.llm is None:
            raise LLMUnavailableError("No LLM available")

        prompt = MULTIMODAL_PROMPT.format(
            draft_text=draft[:2000],
            illustration_prompts=str(illust_prompts)[:1000],
        )

        try:
            response = await self.llm.agenerate([prompt])
            text = response.generations[0][0].text
        except Exception as e:
            raise LLMUnavailableError(f"LLM call failed: {e}") from e

        import json
        try:
            data = json.loads(text)
            info = float(data.get("information_match", 0.5))
            focus = float(data.get("focus_match", 0.5))
            tone = float(data.get("tone_match", 0.5))
            summary = data.get("summary", "")
        except Exception:
            info = focus = tone = 0.5
            summary = "parse failed"

        score = (info + focus + tone) / 3.0 * 100.0

        return SpecialistAuditResult(
            "multimodal",
            round(score, 1),
            feedback={
                "information_match": round(info, 2),
                "focus_match": round(focus, 2),
                "tone_match": round(tone, 2),
                "summary": summary,
            },
            suggestions=[
                "Align illustration focus with text" if focus < 0.6 else None,
                "Match emotional tone in illustrations" if tone < 0.6 else None,
                "Ensure illustration depicts same scene" if info < 0.6 else None,
            ],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        # Rule-based: character bigram overlap between draft and illustration prompts
        draft = ctx.get("draft_text", "") or ""
        illust = ctx.get("illustration_prompts") or ctx.get("illustration_prompt") or ""
        if not draft or not illust:
            return SpecialistAuditResult(
                "multimodal", 50.0,
                feedback={"fallback": "missing draft or illustration"},
                degraded=True,
            )
        def _bigrams(text: str) -> set[str]:
            # Use character bigrams for Japanese
            return {text[i:i+2] for i in range(len(text)-1)}
        draft_bi = _bigrams(draft)
        illust_bi = _bigrams(illust)
        if not draft_bi or not illust_bi:
            return SpecialistAuditResult("multimodal", 50.0, feedback={"fallback": "no bigrams"}, degraded=True)
        overlap = len(draft_bi & illust_bi)
        total = len(draft_bi | illust_bi)
        jaccard = overlap / total if total else 0.0
        score = jaccard * 100.0
        return SpecialistAuditResult(
            "multimodal",
            round(score, 1),
            feedback={
                "fallback": "rule-based bigram Jaccard",
                "draft_bigrams": len(draft_bi),
                "illust_bigrams": len(illust_bi),
                "overlap": overlap,
                "jaccard": round(jaccard, 3),
            },
            degraded=True,
            suggestions=["Increase keyword overlap between text and illustration prompts"] if jaccard < 0.15 else [],
        )


__all__ = ["MultimodalAuditor"]