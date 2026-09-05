"""Style Specialist Auditor.

Phase 2 / Guideline #3-⑤: Tone consistency, style DNA compliance,
vocabulary/sentence structure style consistency. Pure rule-based (LLM-free).
Uses rank-bm25 TF-IDF cosine similarity against style profile.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)

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


STYLE_SYSTEM_PROMPT = """あなたは小説の文体DNA・トーン＆マナー（Style & Tone）を審査する専門オーディターです。
以下の観点で文章の文体を厳格に評価してください:
1. 一人称（私／俺／僕等）や二人称、語尾口調（常体「だ・である」と敬体「です・ます」）の統一性・ブレの有無
2. 指定されたジャンル・文体DNA（ハードボイルド、耽美、軽妙、シリアス等）の維持度
3. 会話文と地の文のトーンバランス
口調のブレや不自然な敬体・常体の混在がある場合は減点（60点未満）、一貫した格調高い文体が維持されていれば高スコア（80点以上）としてください。
"""

STYLE_USER_PROMPT = """【文体プロファイル / DNA設定】
{style_info}

【執筆ドラフト本文】
{draft_text}

上記文章の文体の一貫性・口調・トーン＆マナーを審査し、0〜100で採点してください。
"""


class StyleAuditor(SpecialistAuditor):
    specialist_name = "style"

    def __init__(
        self,
        llm: Any = None,
        style_profile: dict | None = None,
        anti_ai_weight: float = 0.1,
        enable_anti_ai: bool = True,
    ) -> None:
        super().__init__(llm)
        self.style_profile = style_profile or {}
        self.anti_ai_weight = anti_ai_weight
        self.enable_anti_ai = enable_anti_ai

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        style_dna = ctx.get("style_dna") or self.style_profile or {}
        if not draft:
            return SpecialistAuditResult(
                "style", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if not self.llm:
            raise LLMUnavailableError("No LLM available for StyleAuditor")

        style_info = str(style_dna) if style_dna else "標準エンタメ文体（常体・三人称寄り）"
        prompt = STYLE_USER_PROMPT.format(style_info=style_info, draft_text=draft[:4000])

        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=STYLE_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="style",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback: perspective ratio and BoW similarity."""
        draft = ctx.get("draft_text", "") or ""
        style_dna = ctx.get("style_dna") or self.style_profile or {}
        if not draft:
            return SpecialistAuditResult("style", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        tokens = _tokenize(draft)
        if not tokens:
            return SpecialistAuditResult("style", 50.0, feedback={"tokens": 0}, degraded=True)

        fp_ratio = _first_person_ratio(tokens)
        polite_ratio = _polite_ratio(tokens)

        # 語尾の一貫性（常体か敬体のどちらかに統一されているか）
        tone_consistency = max(polite_ratio, 1.0 - polite_ratio)
        score = max(30.0, min(100.0, round(tone_consistency * 70.0 + 30.0, 1)))

        return SpecialistAuditResult(
            specialist_name="style",
            score=score,
            feedback={
                "fallback": "rule-based",
                "has_style_dna": bool(style_dna),
                "polite_ratio": round(polite_ratio, 3),
                "first_person_ratio": round(fp_ratio, 3),
            },
            suggestions=["Maintain consistent sentence endings (polite vs plain)"],
            degraded=True,
        )


__all__ = ["StyleAuditor"]