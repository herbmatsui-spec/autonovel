"""Emotion Curve Specialist Auditor.

Phase 2 / Guideline #3-④: Catharsis achievement, tension variation appropriateness,
emotional arc evaluation. Pure rule-based (LLM-free). Uses emotional vocabulary
from existing emotional_hook_vocabulary.py.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult

# Reuse existing emotional vocabulary if available
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

        # Split into segments (by paragraph or every 200 chars)
        segments = [s.strip() for s in re.split(r"\n\n+|。\s*", draft) if s.strip()]
        if len(segments) < 2:
            segments = [draft[i:i+200] for i in range(0, len(draft), 200)]

        if len(segments) < 2:
            return SpecialistAuditResult(
                "emotion_curve", 30.0,
                feedback={"segments": len(segments), "note": "too short for curve"},
                suggestions=["Need at least 2 segments for emotion curve"],
            )

        # Compute emotional polarity per segment
        polarities = []
        for seg in segments:
            pos = _count_emotion(seg, POSITIVE_EMOTIONS)
            neg = _count_emotion(seg, NEGATIVE_EMOTIONS)
            tens = _count_emotion(seg, TENSION_WORDS)
            cath = _count_emotion(seg, CATHARSIS_WORDS)
            # Net polarity: positive - negative, tension as magnitude
            polarity = (pos - neg) * 0.5 + tens * 0.3 + cath * 0.2
            polarities.append(polarity)

        # Metrics
        if len(polarities) < 2:
            return SpecialistAuditResult("emotion_curve", 30.0, feedback={}, suggestions=[])

        variance = sum((p - sum(polarities)/len(polarities))**2 for p in polarities) / len(polarities)
        amplitude = max(polarities) - min(polarities)
        # Catharsis check: last segment should have high catharsis or polarity shift
        final_catharsis = _count_emotion(segments[-1], CATHARSIS_WORDS)
        start_to_end_shift = polarities[-1] - polarities[0] if polarities else 0

        # Score components (0-100)
        variance_score = min(100, variance * 10)  # up/down variation
        amplitude_score = min(100, amplitude * 5)  # range
        catharsis_score = min(100, final_catharsis * 20)
        shift_score = min(100, abs(start_to_end_shift) * 5)

        total = (
            0.3 * variance_score
            + 0.3 * amplitude_score
            + 0.2 * catharsis_score
            + 0.2 * shift_score
        )

        return SpecialistAuditResult(
            "emotion_curve",
            round(max(0.0, min(100.0, total)), 1),
            feedback={
                "segments": len(segments),
                "polarities": [round(p, 2) for p in polarities],
                "variance": round(variance, 3),
                "amplitude": round(amplitude, 2),
                "final_catharsis_words": final_catharsis,
                "start_end_shift": round(start_to_end_shift, 2),
            },
            suggestions=[
                "Add more emotional variation" if variance_score < 20 else None,
                "Increase emotional range" if amplitude_score < 20 else None,
                "Strengthen catharsis at ending" if catharsis_score < 20 else None,
                "Create clearer emotional arc" if shift_score < 20 else None,
            ],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self.audit(ctx)


__all__ = ["EmotionCurveAuditor"]