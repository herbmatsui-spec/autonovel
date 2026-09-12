"""Multimodal Specialist Auditor.

Phase 2 / Guideline #3-⑧: Illustration prompt / text description consistency.
Checks information amount match, focus alignment, emotional tone consistency.
Evaluated via LLM reasoning with rule-based fallback.
"""

from __future__ import annotations

from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)
from src.agents.specialists.fallback_utils import extract_emotion_triples

MULTIMODAL_SYSTEM_PROMPT = """あなたは小説本文と挿絵（イラスト）プロンプトの整合性・演出効果（Multimodal Alignment）を審査する専門オーディターです。
以下の観点で本文と挿絵指定の一致度を厳格に評価してください:
1. シーン・状況の一致（Scene Alignment）: 挿絵プロンプトが本文のどの場面（クライマックス・決定的瞬間）を描写しているか明確であり、本文の状況と矛盾していないか。
2. 焦点・キャラクターの一致（Focus Alignment）: 本文でスポットライトが当たっている登場人物、表情、ポーズ、視線、服装、小道具が正確に反映されているか。
3. 感情トーン・雰囲気の一致（Tone Consistency）: 本文の緊迫感・悲哀・歓喜などの感情トーンと、挿絵の構図・ライティング指定が共鳴しているか。
本文と無関係なシーンや焦点の乖離、感情トーンの不一致がある場合は低スコア（50点未満）、本文の魅力を最大化する劇的なシンクロがあれば高スコア（80点以上）としてください。
"""

MULTIMODAL_USER_PROMPT = """【執筆ドラフト本文】
{draft_text}

【挿絵プロンプト / イラスト指示】
{illustration_prompts}

上記本文と挿絵指示の焦点・シーン・トーン整合性を審査し、0〜100で採点してください。
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

        if not self.llm:
            raise LLMUnavailableError("No LLM available for MultimodalAuditor")

        prompt = MULTIMODAL_USER_PROMPT.format(
            draft_text=draft[:3000],
            illustration_prompts=str(illust_prompts)[:1500],
        )

        judge_res = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=MULTIMODAL_SYSTEM_PROMPT,
        )
        score, critique, suggestions, confidence, reasoning, raw_resp = judge_res[:6]
        # actionable_diffs = judge_res[6] if len(judge_res) > 6 else []  # not used

        return SpecialistAuditResult(
            specialist_name="multimodal",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback: three-layer matching (character, prop, emotion) between draft and illustration prompts."""
        draft = ctx.get("draft_text", "") or ""
        illust = ctx.get("illustration_prompts") or ctx.get("illustration_prompt") or ""
        if not draft or not illust:
            return SpecialistAuditResult(
                "multimodal", 50.0,
                feedback={"fallback": "missing draft or illustration"},
                degraded=True,
            )

        # Extract emotion triples from both draft and illustration prompts
        draft_triples = extract_emotion_triples(draft)
        illust_triples = extract_emotion_triples(str(illust))

        if not draft_triples or not illust_triples:
            # Fallback to bigram Jaccard if triple extraction fails
            def _bigrams(text: str) -> set[str]:
                return {text[i:i+2] for i in range(len(text)-1)}
            draft_bi = _bigrams(draft)
            illust_bi = _bigrams(str(illust))
            if not draft_bi or not illust_bi:
                return SpecialistAuditResult("multimodal", 50.0, feedback={"fallback": "no bigrams"}, degraded=True)
            overlap = len(draft_bi & illust_bi)
            total = len(draft_bi | illust_bi)
            jaccard = overlap / total if total else 0.0
            score = max(10.0, min(100.0, round(jaccard * 200.0, 1)))
            return SpecialistAuditResult(
                "multimodal",
                score,
                feedback={
                    "fallback": "rule-based bigram Jaccard (triple extraction failed)",
                    "draft_bigrams": len(draft_bi),
                    "illust_bigrams": len(illust_bi),
                    "overlap": overlap,
                    "jaccard": round(jaccard, 3),
                },
                suggestions=["Increase keyword overlap between text and illustration prompts"] if jaccard < 0.15 else [],
                degraded=True,
            )

        # Three-layer Jaccard: character (0.5), prop (0.3), emotion (0.2)
        draft_chars = {t[0] for t in draft_triples}
        illust_chars = {t[0] for t in illust_triples}
        draft_props = {t[1] for t in draft_triples if t[1] != "なし"}
        illust_props = {t[1] for t in illust_triples if t[1] != "なし"}
        draft_emotions = {t[2] for t in draft_triples}
        illust_emotions = {t[2] for t in illust_triples}

        def _jaccard(set1: set, set2: set) -> float:
            if not set1 or not set2:
                return 0.0
            inter = len(set1 & set2)
            union = len(set1 | set2)
            return inter / union if union else 0.0

        char_jaccard = _jaccard(draft_chars, illust_chars)
        prop_jaccard = _jaccard(draft_props, illust_props)
        emotion_jaccard = _jaccard(draft_emotions, illust_emotions)

        # Weighted combination
        score = max(10.0, min(100.0, round((
            0.5 * char_jaccard +
            0.3 * prop_jaccard +
            0.2 * emotion_jaccard
        ) * 200.0, 1)))

        suggs = []
        if char_jaccard < 0.2:
            suggs.append("キャラクターの一致度が低いです。本文と挿絵で同一人物を描写してください")
        if prop_jaccard < 0.2:
            suggs.append("小道具・アイテムの一致度が低いです。本文のアイテムを挿絵に反映してください")
        if emotion_jaccard < 0.2:
            suggs.append("感情トーンの一致度が低いです。本文の感情を挿絵のライティング・構図に反映してください")

        return SpecialistAuditResult(
            "multimodal",
            score,
            feedback={
                "fallback": "rule-based triple-layer Jaccard",
                "draft_triples": len(draft_triples),
                "illust_triples": len(illust_triples),
                "char_jaccard": round(char_jaccard, 3),
                "prop_jaccard": round(prop_jaccard, 3),
                "emotion_jaccard": round(emotion_jaccard, 3),
            },
            suggestions=suggs,
            degraded=True,
        )


__all__ = ["MultimodalAuditor"]