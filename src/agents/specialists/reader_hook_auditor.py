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

# Rhetorical patterns for opening (more sophisticated)
OPENING_RHETORICAL_PATTERNS = {
    "question": [r"[？?]", r"(?:なぜ|どうして|誰|何|どこ|いつ).*(?:だ|です|だろう|だろうか|かな|かね)"],
    "exclamation": [r"[！!]", r"(?:なんと|まさか|信じられ|驚い).*(?:だ|です|た|だった)"],
    "inversion": [r"(?:それは|これが|彼が|彼女が|私が).*(?:だった|であった|なのだ|なのです)"],
    "ellipsis": [r"[…]{2,}", r"……。", r"……、"],
    "crisis": [r"(?:危機|ピンチ|絶体絶命|追い詰め|逃げ|襲わ|迫る).*(?:だ|です|た|だった|ている)"],
    "mystery": [r"(?:謎|不思議|奇妙|違和感|おかしい|秘密|隠さ).*(?:だ|です|た|だった|がある)"],
}

# Rhetorical patterns for ending
ENDING_RHETORICAL_PATTERNS = {
    "unresolved_question": [r"[？?]$", r"(?:どうなる|どうしろ|どうする|なぜ|何が|誰が).*(?:だ|です|だろう|だろうか|かな|かね)$"],
    "cliffhanger": [r"[！!]$", r"(?:見えた|現れた|現れ|扉が|音が|声が|影が).*(?:だ|です|た|だった)$"],
    "ellipsis": [r"[…]{2,}$", r"……。$", r"……、$"],
    "implication": [r"(?:続く|次回|未解決|謎のまま|分からない|わからない|知らされ|気づか).*(?:だ|です|た|だった)$"],
    "sensory": [r"(?:音|声|匂い|香り|光|闇|影|風|雨|雪).*(?:が|は|を|に).*(?:し|する|した|していた|聞こえ|見え|感じ)$"],
}

READER_HOOK_SYSTEM_PROMPT = """あなたはWeb小説・商業小説のリーダビリティと読者牽引力（Reader Hook）を審査する専門オーディターです。
以下の観点で文章の引きの強さを厳格に評価してください:
1. 冒頭の導入力・つかみ（Opening Hook）: 読者が思わず先を読みたくなる謎、違和感、危機的状況、興味深いキャラクターの言動が描かれているか。退屈な説明過多や冗長な導入になっていないか。
2. 末尾のクリフハンガー度（Ending Hook / Cliffhanger）: 次章・次回を今すぐ読みたくなるような未解決の謎の提示、衝撃的な展開の予兆、緊迫したピンチ、または余韻を残す強い引きがあるか。
3. 全体としての読者エンゲージメント維持度。
平坦で退屈な冒頭や、次を読みたいと思わない投げやりな終わり方は低スコア（50点未満）、読者を強力に引き込み離さない構成であれば高スコア（80点以上）としてください。
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
        score, critique, suggestions, confidence, reasoning, raw_resp = await self._judge_with_llm(
            prompt=prompt,
            system_prompt=READER_HOOK_SYSTEM_PROMPT,
        )

        return SpecialistAuditResult(
            specialist_name="reader_hook",
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
            degraded=False,
            confidence=confidence,
            reasoning_trace=reasoning,
            llm_raw_response=raw_resp,
        )

    def _fallback(self, ctx: dict[str, Any]) -> SpecialistAuditResult:
        """Rule-based fallback using rhetorical structure analysis."""
        draft = ctx.get("draft_text", "") or ""
        if not draft:
            return SpecialistAuditResult("reader_hook", 0.0, feedback={"error": "no draft_text"}, degraded=True)

        opening = draft[:300]
        ending = draft[-300:] if len(draft) > 300 else draft

        # Analyze opening rhetorical structure
        opening_analysis = self._analyze_rhetorical_structure(opening, OPENING_RHETORICAL_PATTERNS)
        opening_score = self._compute_hook_score(opening_analysis, is_opening=True)

        # Analyze ending rhetorical structure
        ending_analysis = self._analyze_rhetorical_structure(ending, ENDING_RHETORICAL_PATTERNS)
        ending_score = self._compute_hook_score(ending_analysis, is_opening=False)

        # Also include legacy keyword scoring for backward compatibility
        legacy_opening = self._score_hooks(opening, OPENING_HOOK_PATTERNS, max_score=20)
        legacy_ending = self._score_hooks(ending, ENDING_HOOK_PATTERNS, max_score=30)

        # Weighted combination: 70% rhetorical, 30% legacy keyword
        total = 0.7 * (opening_score + ending_score) + 0.3 * (legacy_opening + legacy_ending)

        suggs = []
        if opening_score < 15:
            suggs.append("冒頭に疑問・危機・違和感などのフックを追加してください")
        if ending_score < 20:
            suggs.append("末尾にクリフハンガー・未解決の謎・示唆を追加してください")

        return SpecialistAuditResult(
            specialist_name="reader_hook",
            score=max(10.0, min(100.0, round(total, 1))),
            feedback={
                "fallback": "rule-based rhetorical analysis",
                "opening_chars": len(opening),
                "ending_chars": len(ending),
                "opening_rhetorical": opening_analysis,
                "ending_rhetorical": ending_analysis,
                "opening_score": round(opening_score, 1),
                "ending_score": round(ending_score, 1),
            },
            suggestions=suggs,
            degraded=True,
        )

    def _analyze_rhetorical_structure(self, text: str, patterns: dict[str, list[str]]) -> dict[str, int]:
        """Count rhetorical pattern matches in text."""
        counts = {}
        for category, pat_list in patterns.items():
            count = 0
            for pat in pat_list:
                count += len(re.findall(pat, text))
            counts[category] = count
        return counts

    def _compute_hook_score(self, analysis: dict[str, int], is_opening: bool) -> float:
        """Compute hook score from rhetorical analysis."""
        if is_opening:
            # Opening: question, mystery, crisis are strong; inversion, ellipsis moderate; exclamation weak
            weights = {
                "question": 15.0,
                "mystery": 15.0,
                "crisis": 12.0,
                "inversion": 8.0,
                "ellipsis": 6.0,
                "exclamation": 5.0,
            }
        else:
            # Ending: cliffhanger, unresolved_question are strong; implication, sensory moderate; ellipsis weak
            weights = {
                "cliffhanger": 20.0,
                "unresolved_question": 18.0,
                "implication": 12.0,
                "sensory": 10.0,
                "ellipsis": 6.0,
            }

        score = 0.0
        for category, count in analysis.items():
            weight = weights.get(category, 3.0)
            # Diminishing returns: first hit full weight, subsequent hits half
            for i in range(count):
                score += weight * (1.0 if i == 0 else 0.5)

        return min(50.0, score)  # Cap at 50 each (total 100)

    def _score_hooks(self, text: str, patterns: list[str], max_score: float) -> float:
        if not text:
            return 0.0
        hits = sum(1 for p in patterns if re.search(p, text))
        score = 0.0
        for i in range(hits):
            score += max_score * (1.0 / (i + 1)) * 0.4
        return min(max_score, score)


__all__ = ["ReaderHookAuditor"]