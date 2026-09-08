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
    ActionableDiff,
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
    polite = sum(1 for t in tokens if t.endswith(("です", "ます", "でした", "ました", "ません", "でしょうか")))
    return polite / max(1, len(tokens))


STYLE_SYSTEM_PROMPT = """あなたは小説の文体DNA・トーン＆マナー（Style & Tone）を審査する専門オーディターです。
以下の観点で文章の文体を厳格に評価してください:
1. 一人称（私／俺／僕等）や二人称、語尾口調（常体「だ・である」と敬体「です・ます」）の統一性・ブレの有無
2. 指定されたジャンル・文体DNA（ハードボイルド、耽美、軽妙、シリアス等）の維持度
3. 会話文と地の文のトーンバランス
口調のブレや不自然な敬体・常体の混在がある場合は減点（60点未満）、一貫した格調高い文体が維持されていれば高スコア（80点以上）としてください。

【Actionable Diff の必須出力要件】
文体のブレ（常体・敬体の混在、不自然な一人称のズレ、地の文と会話の違和感など）がある箇所について、
問題のある原文の抜粋と、文体を統一・昇華させた具体的なリライト文（ActionableDiff）を1〜3件必ず含めてください。
"""

STYLE_USER_PROMPT = """【文体プロファイル / DNA設定】
{style_info}

【執筆ドラフト本文】
{draft_text}

上記文章の文体の一貫性・口調・トーン＆マナーを審査し、0〜100で採点してください。
文体ブレの修正箇所について、具体的な Actionable Diff を必ず含めてください。
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

        if len(draft) <= 3500:
            audited_text = draft
        else:
            sections = self.section_extractor.extract_four_sections(draft, section_chars=800)
            audited_text = (
                f"【総文字数】{len(draft)}文字（章全体からサンプリングした代表セクション群）\n\n"
                + "\n\n---\n\n".join(f"【{s.name.upper()}セクション】\n{s.text}" for s in sections)
            )

        prompt = STYLE_USER_PROMPT.format(style_info=style_info, draft_text=audited_text)

        judge_res = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=STYLE_SYSTEM_PROMPT,
        )
        score, critique, suggestions, confidence, reasoning, raw_resp = judge_res[:6]
        actionable_diffs = judge_res[6] if len(judge_res) > 6 else []

        return SpecialistAuditResult(
            specialist_name="style",
            score=score,
            feedback={
                "critique": critique,
                "total_chars": len(draft),
                "audited_chars": len(audited_text),
            },
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
            actionable_diffs=actionable_diffs,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback: perspective ratio, BoW similarity, and BM25 against style DNA."""
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

        # BM25 similarity against style_dna sample_text if available
        bm25_score = 0.0
        sample_text = style_dna.get("sample_text") if isinstance(style_dna, dict) else None
        if sample_text and BM25Okapi is not None:
            sample_tokens = _tokenize(sample_text)
            if sample_tokens:
                bm25 = BM25Okapi([sample_tokens])
                bm25_score = bm25.get_scores(tokens)[0] if tokens else 0.0
                # Normalize BM25 score (typically 0-10 range, cap at 1.0)
                bm25_score = min(1.0, bm25_score / 10.0)

        # Combined score: 70% tone consistency, 30% BM25 similarity
        # Raise threshold: tone_consistency >= 0.8 for high score
        base_score = tone_consistency * 65.0 + 30.0  # Max 95 when tone_consistency=1.0
        if bm25_score > 0:
            base_score = 0.7 * base_score + 0.3 * (bm25_score * 100.0)

        score = max(30.0, min(95.0, round(base_score, 1)))

        suggestions = ["Maintain consistent sentence endings (polite vs plain)"]
        diffs: list[ActionableDiff] = []

        # 敬体・常体混在の検出とリライト提案
        if tone_consistency < 0.85:
            suggestions.append("Unify sentence endings to either polite (desu/masu) or plain (da/dearu) form")
            # 少数派の語尾を持つ文を抽出
            sentences = [s.strip() for s in re.split(r"[。！？\n]+", draft) if s.strip()]
            target_is_plain = polite_ratio < 0.5  # 常体に統一すべき
            for sent in sentences:
                if target_is_plain and sent.endswith(("です", "ます", "でした", "ました")):
                    # 敬体を常体に変換する提案
                    converted = re.sub(r"でした$", "だった", sent)
                    converted = re.sub(r"ました$", "た", converted)
                    converted = re.sub(r"です$", "だ", converted)
                    converted = re.sub(r"ます$", "る", converted)
                    diffs.append(
                        ActionableDiff(
                            location="文末語尾（常体主体の地の文）",
                            original_quote=sent,
                            improved_suggestion=converted,
                            rationale="地の文は常体（だ・である）が基調ですが、敬体（です・ます）が混在しているため統一。",
                        )
                    )
                    break
                elif not target_is_plain and (sent.endswith(("だ", "である", "た", "いた", "った")) and not sent.endswith(("です", "ます", "でした", "ました"))):
                    diffs.append(
                        ActionableDiff(
                            location="文末語尾（敬体主体の文）",
                            original_quote=sent,
                            improved_suggestion=f"{sent}です",
                            rationale="敬体（です・ます）主体の文脈で常体が混在しているため統一。",
                        )
                    )
                    break

        # 一人称混在チェック
        fps_found = [p for p in ("私", "俺", "僕", "あたし", "わし") if p in draft]
        if len(fps_found) >= 2:
            suggestions.append(f"Multiple first-person pronouns detected: {fps_found}")
            diffs.append(
                ActionableDiff(
                    location="一人称代名詞",
                    original_quote=" / ".join(fps_found),
                    improved_suggestion=f"主人公の一人称を「{fps_found[0]}」に一本化する。",
                    rationale=f"同一視点内で複数の異なる一人称（{', '.join(fps_found)}）が混在し視点ブレが発生しているため。",
                )
            )

        if bm25_score > 0 and bm25_score < 0.3:
            suggestions.append("Vocabulary/style diverges from style_dna sample_text")

        return SpecialistAuditResult(
            specialist_name="style",
            score=score,
            feedback={
                "fallback": "rule-based",
                "has_style_dna": bool(style_dna),
                "polite_ratio": round(polite_ratio, 3),
                "first_person_ratio": round(fp_ratio, 3),
                "tone_consistency": round(tone_consistency, 3),
                "bm25_similarity": round(bm25_score, 3) if bm25_score > 0 else None,
            },
            suggestions=suggestions,
            degraded=True,
            actionable_diffs=diffs,
        )


__all__ = ["StyleAuditor"]