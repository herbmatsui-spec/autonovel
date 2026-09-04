"""Style Specialist Auditor.

Phase 2 / Guideline #3-⑤: Tone consistency, style DNA compliance,
vocabulary/sentence structure style consistency. Pure rule-based (LLM-free).
Uses rank-bm25 TF-IDF cosine similarity against style profile.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None


def _tokenize(text: str) -> list[str]:
    """Japanese word tokenization: split on punctuation and whitespace."""
    return [t for t in re.split(r"[、。,\s\n]+", text) if t]


def _bow(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    if not vec1 or not vec2:
        return 0.0
    keys = set(vec1.keys()) | set(vec2.keys())
    dot = sum(vec1[k] * vec2[k] for k in keys)
    norm1 = sum(v * v for v in vec1.values()) ** 0.5
    norm2 = sum(v * v for v in vec2.values()) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _first_person_ratio(tokens: list[str]) -> float:
    fp = sum(1 for t in tokens if t in ("私", "俺", "僕", "あたし", "わし", "自分"))
    return fp / max(1, len(tokens))


def _polite_ratio(tokens: list[str]) -> float:
    polite = sum(1 for t in tokens if t.endswith(("です", "ます", "でした", "まし")) )
    return polite / max(1, len(tokens))


class StyleAuditor(SpecialistAuditor):
    specialist_name = "style"

    def __init__(self, llm: Any = None, style_profile: dict | None = None) -> None:
        super().__init__(llm)
        self.style_profile = style_profile or {}

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        style_dna = ctx.get("style_dna") or self.style_profile or {}
        if not draft:
            return SpecialistAuditResult(
                "style", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        tokens = _tokenize(draft)
        if not tokens:
            return SpecialistAuditResult(
                "style", 50.0,
                feedback={"tokens": 0},
                suggestions=["Text too short"],
            )

        # Build BoW for draft
        draft_bow = _bow(tokens)

        # Build BoW for style profile (if available)
        style_tokens = _tokenize(style_dna.get("sample_text", "")) if isinstance(style_dna, dict) else []
        style_bow = _bow(style_tokens) if style_tokens else draft_bow

        # TF-IDF style cosine similarity
        if BM25Okapi and style_tokens:
            # Use BM25 as TF-IDF proxy
            corpus = [style_tokens, tokens]
            bm25 = BM25Okapi(corpus)
            # Score draft against style corpus
            scores = bm25.get_scores(tokens)
            style_similarity = float(scores[0]) if len(scores) > 0 else 0.0
            # Normalize to 0-1 (rough)
            style_similarity = min(1.0, style_similarity / 10.0)
        else:
            style_similarity = _cosine_similarity(draft_bow, style_bow)

        # Perspective consistency
        fp_ratio = _first_person_ratio(tokens)
        polite_ratio = _polite_ratio(tokens)

        # Check if perspective matches style profile
        expected_fp = style_dna.get("first_person", 0.5) if isinstance(style_dna, dict) else 0.5
        expected_polite = style_dna.get("polite", 0.5) if isinstance(style_dna, dict) else 0.5
        fp_consistency = 1.0 - abs(fp_ratio - expected_fp)
        polite_consistency = 1.0 - abs(polite_ratio - expected_polite)

        # Combined score
        score = (
            0.5 * style_similarity
            + 0.25 * fp_consistency
            + 0.25 * polite_consistency
        ) * 100.0

        return SpecialistAuditResult(
            "style",
            round(max(0.0, min(100.0, score)), 1),
            feedback={
                "tokens": len(tokens),
                "style_similarity": round(style_similarity, 3),
                "first_person_ratio": round(fp_ratio, 3),
                "polite_ratio": round(polite_ratio, 3),
                "fp_consistency": round(fp_consistency, 3),
                "polite_consistency": round(polite_consistency, 3),
            },
            suggestions=[
                "Align vocabulary with style DNA" if style_similarity < 0.5 else None,
                "Check perspective consistency" if fp_consistency < 0.7 else None,
                "Check politeness consistency" if polite_consistency < 0.7 else None,
            ],
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        return self.audit(ctx)


__all__ = ["StyleAuditor"]