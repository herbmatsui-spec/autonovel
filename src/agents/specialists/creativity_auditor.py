"""Creativity Specialist Auditor.

Phase 2 / Guideline #3-②: Novel expressions, metaphor diversity, uniqueness.
Pure rule-based (LLM-free). Uses Type-Token Ratio, n-gram repetition, POS diversity.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult


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

        tokens = _tokenize(draft)
        if not tokens:
            return SpecialistAuditResult(
                "creativity", 0.0,
                feedback={"tokens": 0},
                suggestions=["Text too short to evaluate"],
            )

        ttr = _type_token_ratio(tokens)
        rep4 = _ngram_repetition(tokens, 4)
        pos_div = _pos_diversity(draft)

        # Weighted creativity score
        # High TTR = good, Low repetition = good, High POS diversity = good
        score = (
            0.4 * ttr
            + 0.3 * (1.0 - rep4)
            + 0.3 * pos_div
        ) * 100.0

        return SpecialistAuditResult(
            "creativity",
            round(max(0.0, min(100.0, score)), 1),
            feedback={
                "tokens": len(tokens),
                "unique_tokens": len(set(tokens)),
                "ttr": round(ttr, 3),
                "rep_4gram": round(rep4, 3),
                "pos_diversity": round(pos_div, 3),
            },
            suggestions=[
                "Vary vocabulary" if ttr < 0.4 else None,
                "Avoid repetitive phrases" if rep4 > 0.3 else None,
                "Use more descriptive adjectives/adverbs" if pos_div < 0.1 else None,
            ],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self.audit(ctx)


__all__ = ["CreativityAuditor"]