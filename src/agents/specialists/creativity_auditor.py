"""Creativity Specialist Auditor.

Phase 2 / Guideline #3-②: Novel expressions, metaphor diversity, uniqueness.
Pure rule-based (LLM-free). Uses Type-Token Ratio, n-gram repetition, POS diversity.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)



# Simple POS tagger patterns for Japanese
ADJ_PATTERN = re.compile(r"(?:[^。]*?)(?:い|な)(?:だ|です|でした|だった|だっ|だろ|だろう|なら|に|な|だ|で|でし|です|だっ|たり|た|だ|だ)")
ADV_PATTERN = re.compile(r"(?:[^。]*?)(?:に|く|で|して|も|でも|し|しい|しい|する|した|す|しろ|せよ|せず|せぬ|せん|せまい|せん)")
# Verb-ending patterns for Japanese verbs (simplified)
VERB_ENDINGS = ("う", "く", "ぐ", "す", "つ", "ぬ", "ぶ", "む", "る")


def _tokenize(text: str) -> list[str]:
    """Simple word tokenizer for Japanese: split on punctuation/whitespace."""
    # Split on Japanese punctuation and whitespace
    return [t for t in re.split(r"[、。,\s\n]+", text) if t]


def _type_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _ngram_repetition(tokens: list[str], n: int = 4) -> float:
    """Fraction of repeated n-grams (0 = no repetition, 1 = all same)."""
    if len(tokens) < n:
        return 0.0
    ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
    if not ngrams:
        return 0.0
    unique = len(set(ngrams))
    return 1.0 - (unique / len(ngrams))


def _pos_diversity(text: str) -> float:
    """Heuristic POS diversity: ratio of adjective/adverb-like tokens."""
    # Very rough: count words ending in typical adjective/adverb endings
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    adj_count = sum(1 for t in tokens if t.endswith(("い", "な", "だ", "です", "だった")))
    adv_count = sum(1 for t in tokens if t.endswith(("に", "く", "で", "して", "も")))
    return min(1.0, (adj_count + adv_count) / max(1, len(tokens)) * 2.0)


CREATIVITY_SYSTEM_PROMPT = """あなたは文学・エンタメ小説の独創性・表現力（Creativity）を審査する専門オーディターです。
以下の観点で文章の創造性を厳格に評価してください:
1. 比喩・メタファーの独創性と鮮烈さ（ありふれた常套句・陳腐なクリシェの乱用がないか）
2. 語彙の豊かさと情景描写の多面性
3. 予想を心地よく裏切る意外性やユニークな表現
単調で紋切り型の表現ばかりの文章は低スコア（50点未満）、鮮烈で心に残る独創的な表現があれば高スコア（80点以上）としてください。
"""

CREATIVITY_USER_PROMPT = """【執筆ドラフト本文】
{draft_text}

上記文章の表現の独創性・比喩の新鮮さ・語彙の多様性を審査し、0〜100で採点してください。
"""


class CreativityAuditor(SpecialistAuditor):
    specialist_name = "creativity"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "creativity", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if not self.llm:
            raise LLMUnavailableError("No LLM available for CreativityAuditor")

        prompt = CREATIVITY_USER_PROMPT.format(draft_text=draft[:4000])
        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=CREATIVITY_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="creativity",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using Type-Token Ratio, n-gram repetition, and POS diversity."""
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult("creativity", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        tokens = _tokenize(draft)
        if not tokens:
            return SpecialistAuditResult("creativity", 50.0, feedback={"tokens": 0}, degraded=True)

        ttr = _type_token_ratio(tokens)
        rep4 = _ngram_repetition(tokens, 4)
        pos_div = _pos_diversity(draft)

        score = (0.4 * ttr + 0.3 * (1.0 - rep4) + 0.3 * pos_div) * 100.0
        score = max(0.0, min(100.0, round(score, 1)))

        return SpecialistAuditResult(
            specialist_name="creativity",
            score=score,
            feedback={
                "fallback": "rule-based",
                "tokens": len(tokens),
                "unique_tokens": len(set(tokens)),
                "ttr": round(ttr, 3),
                "rep_4gram": round(rep4, 3),
                "pos_diversity": round(pos_div, 3),
            },
            suggestions=["Vary vocabulary and metaphors"] if ttr < 0.4 else [],
            degraded=True,
        )


__all__ = ["CreativityAuditor"]