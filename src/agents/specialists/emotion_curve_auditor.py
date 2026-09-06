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

# Negation words that flip catharsis/positive meaning
NEGATION_WORDS = {"ない", "なく", "ぬ", "ず", "ね", "ません", "ませんでした", "なかった", "なく", "ずに", "ずとも"}


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
        score, critique, suggestions, confidence, reasoning, raw_resp = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=EMOTION_CURVE_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="emotion_curve",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using emotional vocabulary and polarity curve with improved segmentation."""
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult("emotion_curve", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        # Split into segments by emotional density change points (paragraph boundaries + emotional word density shifts)
        segments = self._split_by_emotional_shifts(draft)
        if len(segments) < 2:
            segments = [draft[i:i+200] for i in range(0, len(draft), 200)]

        if len(segments) < 2:
            return SpecialistAuditResult(
                "emotion_curve", 35.0,
                feedback={"fallback": "rule-based", "segments": len(segments), "note": "too short for curve"},
                suggestions=["Need at least 2 segments for emotion curve"],
                degraded=True,
            )

        # Compute emotional polarity per segment
        polarities = []
        catharsis_counts = []
        for seg in segments:
            pos = _count_emotion(seg, POSITIVE_EMOTIONS)
            neg = _count_emotion(seg, NEGATIVE_EMOTIONS)
            tens = _count_emotion(seg, TENSION_WORDS)
            # Catharsis with negation check
            cath = self._count_catharsis_with_negation(seg)
            catharsis_counts.append(cath)
            polarity = (pos - neg) * 0.5 + tens * 0.3 + cath * 0.2
            polarities.append(polarity)

        if len(polarities) < 2:
            return SpecialistAuditResult("emotion_curve", 35.0, feedback={"fallback": "rule-based"}, suggestions=[], degraded=True)

        variance = sum((p - sum(polarities)/len(polarities))**2 for p in polarities) / len(polarities)
        amplitude = max(polarities) - min(polarities)
        final_catharsis = catharsis_counts[-1] if catharsis_counts else 0
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
            score=round(max(35.0, min(100.0, total)), 1),
            feedback={
                "fallback": "rule-based improved segmentation + negation-aware catharsis",
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

    def _split_by_emotional_shifts(self, text: str) -> list[str]:
        """Split text by paragraph boundaries and emotional density shifts."""
        # First split by paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        if len(paragraphs) >= 3:
            return paragraphs

        # If too few paragraphs, split by sentence and group by emotional density
        sentences = [s.strip() for s in re.split(r"[。！？]", text) if s.strip()]
        if len(sentences) < 4:
            return [text[i:i+200] for i in range(0, len(text), 200)]

        # Compute emotional density per sentence
        densities = []
        for sent in sentences:
            density = (
                _count_emotion(sent, POSITIVE_EMOTIONS) +
                _count_emotion(sent, NEGATIVE_EMOTIONS) +
                _count_emotion(sent, TENSION_WORDS) +
                _count_emotion(sent, CATHARSIS_WORDS)
            )
            densities.append(density)

        # Find shift points (where density changes significantly)
        segments = []
        current_segment = [sentences[0]]
        current_density = densities[0]

        for i in range(1, len(sentences)):
            density = densities[i]
            # If density change > 50% of max density, start new segment
            max_density = max(densities) if max(densities) > 0 else 1
            if abs(density - current_density) > max_density * 0.5:
                segments.append("。".join(current_segment) + "。")
                current_segment = [sentences[i]]
                current_density = density
            else:
                current_segment.append(sentences[i])
                current_density = (current_density * len(current_segment) + density) / (len(current_segment) + 1)

        if current_segment:
            segments.append("。".join(current_segment) + "。")

        return segments if len(segments) >= 2 else [text[i:i+200] for i in range(0, len(text), 200)]

    def _count_catharsis_with_negation(self, text: str) -> int:
        """Count catharsis words, excluding those preceded by negation within 3 chars."""
        count = 0
        for word in CATHARSIS_WORDS:
            for match in re.finditer(re.escape(word), text):
                start = match.start()
                # Check for negation before the word
                context_start = max(0, start - 3)
                context = text[context_start:start]
                if not any(neg in context for neg in NEGATION_WORDS):
                    count += 1
        return count


__all__ = ["EmotionCurveAuditor"]