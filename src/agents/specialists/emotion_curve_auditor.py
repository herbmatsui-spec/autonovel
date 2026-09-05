"""Emotion Curve Specialist Auditor.

Phase 2 / Guideline #3-④: Catharsis achievement, tension variation appropriateness,
emotional arc evaluation. Evaluated via LLM reasoning with rule-based fallback.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)

# Reuse existing emotional vocabulary for fallback
try:
    from src.config.emotional_hook_vocabulary import (
        POSITIVE_EMOTIONS,
        NEGATIVE_EMOTIONS,
        TENSION_WORDS,
        CATHARSIS_WORDS,
    )
except Exception:
    POSITIVE_EMOTIONS = {"喜", "楽", "幸", "愛", "希望", "光", "笑", "温", "優", "安"}
    NEGATIVE_EMOTIONS = {"悲", "苦", "痛", "怒", "恐", "闇", "冷", "絶望", "孤独", "哀"}
    TENSION_WORDS = {"緊張", "不安", "焦", "追い詰め", "危機", "ピンチ", "戦", "闘", "衝突", "対立"}
    CATHARSIS_WORDS = {"解放", "安堵", "救い", "光", "希望", "勝利", "和解", "癒", "涙", "感動"}


def _count_emotion(text: str, word_set: set[str]) -> int:
    count = 0
    for w in word_set:
        count += len(re.findall(re.escape(w), text))
    return count


EMOTION_CURVE_SYSTEM_PROMPT = """あなたは小説の感情曲線・情動ダイナミクス（Emotion Curve & Catharsis）を審査する専門オーディターです。
以下の観点で文章の感情的起伏とカタルシスを厳格に評価してください:
1. 感情の起伏とダイナミクス（Tension Variation）: 平坦で起伏のない単調な描写が続いていないか。緊張（ピンチ・葛藤・不安）と緩和（安堵・日常）のバランスが良いか。
2. カタルシス・解放感（Catharsis Achievement）: 読者の感情が高まった後に、納得感・救い・爽快感・深い余韻などの感情的報酬が適切にもたらされているか。
3. キャラクターの内面の情動が読者に伝播する説得力。
終始起伏がなく単調な文章や感情が死んでいる文章は低スコア（50点未満）、感情のジェットコースターや鮮烈なカタルシスを描けている場合は高スコア（80点以上）としてください。
"""

EMOTION_CURVE_USER_PROMPT = """【執筆ドラフト本文】
{draft_text}

上記文章の感情の起伏（テンションの上下）と結末部のカタルシス（感情の解放・余韻）を審査し、0〜100で採点してください。
"""


class EmotionCurveAuditor(SpecialistAuditor):
    specialist_name = "emotion_curve"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "emotion_curve", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if not self.llm:
            raise LLMUnavailableError("No LLM available for EmotionCurveAuditor")

        prompt = EMOTION_CURVE_USER_PROMPT.format(draft_text=draft[:4000])
        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=EMOTION_CURVE_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="emotion_curve",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using emotional vocabulary and polarity curve."""
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult("emotion_curve", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        # Split into segments (by paragraph or every 200 chars)
        segments = [s.strip() for s in re.split(r"\n\n+|。\s*", draft) if s.strip()]
        if len(segments) < 2:
            segments = [draft[i:i+200] for i in range(0, len(draft), 200)]

        if len(segments) < 2:
            return SpecialistAuditResult(
                "emotion_curve", 30.0,
                feedback={"fallback": "rule-based", "segments": len(segments), "note": "too short for curve"},
                suggestions=["Need at least 2 segments for emotion curve"],
                degraded=True,
            )

        # Compute emotional polarity per segment
        polarities = []
        for seg in segments:
            pos = _count_emotion(seg, POSITIVE_EMOTIONS)
            neg = _count_emotion(seg, NEGATIVE_EMOTIONS)
            tens = _count_emotion(seg, TENSION_WORDS)
            cath = _count_emotion(seg, CATHARSIS_WORDS)
            polarity = (pos - neg) * 0.5 + tens * 0.3 + cath * 0.2
            polarities.append(polarity)

        if len(polarities) < 2:
            return SpecialistAuditResult("emotion_curve", 30.0, feedback={"fallback": "rule-based"}, suggestions=[], degraded=True)

        variance = sum((p - sum(polarities)/len(polarities))**2 for p in polarities) / len(polarities)
        amplitude = max(polarities) - min(polarities)
        final_catharsis = _count_emotion(segments[-1], CATHARSIS_WORDS)
        start_to_end_shift = polarities[-1] - polarities[0] if polarities else 0

        variance_score = min(100, variance * 10)
        amplitude_score = min(100, amplitude * 5)
        catharsis_score = min(100, final_catharsis * 20)
        shift_score = min(100, abs(start_to_end_shift) * 5)

        total = (
            0.3 * variance_score
            + 0.3 * amplitude_score
            + 0.2 * catharsis_score
            + 0.2 * shift_score
        )

        suggs = []
        if variance_score < 20:
            suggs.append("Add more emotional variation")
        if amplitude_score < 20:
            suggs.append("Increase emotional range")
        if catharsis_score < 20:
            suggs.append("Strengthen catharsis at ending")
        if shift_score < 20:
            suggs.append("Create clearer emotional arc")

        return SpecialistAuditResult(
            specialist_name="emotion_curve",
            score=round(max(20.0, min(100.0, total)), 1),
            feedback={
                "fallback": "rule-based",
                "segments": len(segments),
                "polarities": [round(p, 2) for p in polarities],
                "variance": round(variance, 3),
                "amplitude": round(amplitude, 2),
                "final_catharsis_words": final_catharsis,
                "start_end_shift": round(start_to_end_shift, 2),
            },
            suggestions=suggs,
            degraded=True,
        )


__all__ = ["EmotionCurveAuditor"]