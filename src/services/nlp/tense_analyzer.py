"""Tense and Context Analyzer for Japanese prose."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class TenseAnalysisResult:
    """Analysis result of tense distribution in a paragraph."""
    dominant_tense: str                     # "PAST", "PRESENT", "MIXED", "NEUTRAL"
    past_ratio: float                       # Ratio of past-tense sentences (0.0 to 1.0)
    present_ratio: float                    # Ratio of present-tense sentences (0.0 to 1.0)
    is_past_locked: bool                    # True if past tense should be strictly preserved
    sentence_tenses: List[str] = field(default_factory=list)  # ["PAST", "PRESENT", "OTHER", ...]


class TenseContextAnalyzer:
    """Analyzes paragraph and sentence level grammatical tense in Japanese prose."""

    # 過去形・完了文末パターン
    PAST_ENDINGS = (
        "た。", "いた。", "った。", "れた。", "せた。",
        "だった。", "であった。", "のだった。", "のだっ[たた]？",
        "ていた。", "していた。", "きわまった。", "おわった。"
    )

    # 現在形・動詞終止形文末パターン
    PRESENT_ENDINGS = (
        "る。", "す。", "く。", "む。", "う。", "つ。", "ぬ。", "ぶ。",
        "である。", "です。", "ます。", "のだ。", "ことだ。"
    )

    def __init__(self, past_lock_threshold: float = 0.65) -> None:
        self.past_lock_threshold = past_lock_threshold

    def analyze_sentence_tense(self, sentence: str) -> str:
        """Classify single sentence ending tense."""
        s = sentence.strip()
        if not s:
            return "NEUTRAL"

        # 会話文は時制分析から除外
        if s.startswith("「") or s.startswith("『"):
            return "DIALOGUE"

        # 体言止め（名詞・記号で終了）
        if not re.search(r"[。！？!?]$", s):
            return "OTHER"

        for p in self.PAST_ENDINGS:
            if s.endswith(p):
                return "PAST"

        for pr in self.PRESENT_ENDINGS:
            if s.endswith(pr):
                return "PRESENT"

        # 助詞・体言止め
        return "OTHER"

    def analyze_paragraph(self, paragraph: str) -> TenseAnalysisResult:
        """Analyze tense distribution across a full paragraph."""
        p = paragraph.strip()
        if not p:
            return TenseAnalysisResult(
                dominant_tense="NEUTRAL",
                past_ratio=0.0,
                present_ratio=0.0,
                is_past_locked=False,
                sentence_tenses=[]
            )

        # 句点で文分割
        raw_sentences = re.split(r"(?<=[。！？!?])", p)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return TenseAnalysisResult(
                dominant_tense="NEUTRAL",
                past_ratio=0.0,
                present_ratio=0.0,
                is_past_locked=False,
                sentence_tenses=[]
            )

        tenses = [self.analyze_sentence_tense(s) for s in sentences]
        evaluable = [t for t in tenses if t in ("PAST", "PRESENT")]

        if not evaluable:
            return TenseAnalysisResult(
                dominant_tense="NEUTRAL",
                past_ratio=0.0,
                present_ratio=0.0,
                is_past_locked=False,
                sentence_tenses=tenses
            )

        past_count = sum(1 for t in evaluable if t == "PAST")
        present_count = sum(1 for t in evaluable if t == "PRESENT")
        total_evaluable = len(evaluable)

        past_ratio = round(past_count / total_evaluable, 3)
        present_ratio = round(present_count / total_evaluable, 3)

        is_past_locked = past_ratio >= self.past_lock_threshold

        if is_past_locked:
            dominant = "PAST"
        elif present_ratio >= 0.65:
            dominant = "PRESENT"
        else:
            dominant = "MIXED"

        return TenseAnalysisResult(
            dominant_tense=dominant,
            past_ratio=past_ratio,
            present_ratio=present_ratio,
            is_past_locked=is_past_locked,
            sentence_tenses=tenses
        )
