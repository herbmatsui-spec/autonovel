"""Reader Hook Specialist Auditor.

Phase 2 / Guideline #3-③: Opening hook strength (mystery/discomfort/crisis) and
ending cliffhanger score. Evaluated via LLM reasoning with rule-based fallback.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)

# Hook keywords for opening (used in fallback)
OPENING_HOOK_PATTERNS = [
    r"なぜ", r"どうして", r"誰", r"何", r"どこ", r"いつ",
    r"謎", r"不思議", r"奇妙", r"違和感", r"おかしい",
    r"危機", r"ピンチ", r"絶体絶命", r"追い詰め", r"逃げ",
    r"突然", r"唐突", r"一瞬", r"瞬間", r"衝撃",
    r"？", r"！", r"…", r"……",
]

# Hook keywords for ending (used in fallback)
ENDING_HOOK_PATTERNS = [
    r"…$", r"……$", r"？$", r"！$",
    r"どうなる", r"どうしろ", r"どうする", r"続く", r"次回",
    r"未解決", r"謎のまま", r"分からない", r"わからない",
    r"見えた", r"現れた", r"現れ", r"扉が", r"音が",
]

READER_HOOK_SYSTEM_PROMPT = """あなたはWeb小説・商業小説のリーダビリティと読者牽引力（Reader Hook）を審査する専門オーディターです。
以下の観点で文章の引きの強さを厳格に評価してください:
1. 冒頭の導入力・つかみ（Opening Hook）: 読者が思わず先を読みたくなる謎、違和感、危機的状況、興味深いキャラクターの言動が描かれているか。退屈な説明過多や冗長な導入になっていないか。
2. 末尾のクリフハンガー度（Ending Hook / Cliffhanger）: 次章・次回を今すぐ読みたくなるような未解決の謎の提示、衝撃的な展開の予兆、緊迫したピンチ、または余韻を残す強い引きがあるか。
3. 全体としての読者エンゲージメント維持度。
平坦で退屈な冒頭や、次を読みたいと思わせない投げやりな終わり方は低スコア（50点未満）、読者を強力に引き込み離さない構成であれば高スコア（80点以上）としてください。
"""

READER_HOOK_USER_PROMPT = """【執筆ドラフト本文】
{draft_text}

上記文章の冒頭の引きの強さと末尾のクリフハンガー（次話への牽引力）を審査し、0〜100で採点してください。
"""


class ReaderHookAuditor(SpecialistAuditor):
    specialist_name = "reader_hook"

    async def audit(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult(
                "reader_hook", 0.0,
                feedback={"error": "no draft_text"},
                suggestions=["Provide draft_text in context"],
            )

        if not self.llm:
            raise LLMUnavailableError("No LLM available for ReaderHookAuditor")

        prompt = READER_HOOK_USER_PROMPT.format(draft_text=draft[:4000])
        score, critique, suggestions = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=READER_HOOK_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="reader_hook",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using keyword patterns in opening and ending."""
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult("reader_hook", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        opening = draft[:200]
        ending = draft[-200:] if len(draft) > 200 else draft

        opening_score = self._score_hooks(opening, OPENING_HOOK_PATTERNS, max_score=40)
        ending_score = self._score_hooks(ending, ENDING_HOOK_PATTERNS, max_score=60)
        total = opening_score + ending_score

        suggs = []
        if opening_score < 20:
            suggs.append("Strengthen opening hook with a question or crisis")
        if ending_score < 30:
            suggs.append("Add cliffhanger or unresolved question at end")

        return SpecialistAuditResult(
            specialist_name="reader_hook",
            score=max(10.0, min(100.0, round(total, 1))),
            feedback={
                "fallback": "rule-based",
                "opening_chars": len(opening),
                "ending_chars": len(ending),
                "opening_score": round(opening_score, 1),
                "ending_score": round(ending_score, 1),
            },
            suggestions=suggs,
            degraded=True,
        )

    def _score_hooks(self, text: str, patterns: list[str], max_score: float) -> float:
        if not text:
            return 0.0
        hits = sum(1 for p in patterns if re.search(p, text))
        score = 0.0
        for i in range(hits):
            score += max_score * (1.0 / (i + 1)) * 0.4
        return min(max_score, score)


__all__ = ["ReaderHookAuditor"]