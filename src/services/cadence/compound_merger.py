"""Compound Sentence Merger for reducing repetitive sentence endings."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


class CompoundSentenceMerger:
    """Safely merges consecutive short sentences using conjunctive forms (連用形・接続)."""

    # 動詞・助動詞の連用形変換マップ (末尾 -> 連用形接続)
    CONJUNCTIVE_MAP = [
        # 〜ていた -> 〜ており、
        (r"ていた[。]$", "ており、"),
        (r"していた[。]$", "しており、"),
        # 〜だった -> 〜であり、
        (r"だった[。]$", "であり、"),
        (r"であった[。]$", "であって、"),
        # 〜カ行イ音便: 書いた -> 書き、
        (r"いた[。]$", "き、"),
        # 〜サ行: 起こした -> 起こし、 / 決意した -> 決意し、
        (r"した[。]$", "し、"),
        # 〜タ行・ラ行促音便: 走った -> 走り、 / 勝った -> 勝ち、
        (r"った[。]$", "り、"),
        # 〜マ行・バ行撥音便: 飛んだ -> 飛び、 / 読んだ -> 読み、
        (r"んだ[。]$", "み、"),
        # 〜一段動詞: 見た -> 見て、 / 逃げた -> 逃げ、 / 伝えた -> 伝え、
        (r"えた[。]$", "え、"),
        (r"けた[。]$", "け、"),
        (r"めた[。]$", "め、"),
        (r"れた[。]$", "れ、"),
        (r"せた[。]$", "せ、"),
    ]

    def __init__(self, max_chars: int = 60) -> None:
        self.max_chars = max_chars

    def can_merge(self, s1: str, s2: str, max_chars: Optional[int] = None) -> bool:
        """Check if two sentences are suitable for compound merging."""
        limit = max_chars if max_chars is not None else self.max_chars
        s1 = s1.strip()
        s2 = s2.strip()

        if not s1 or not s2:
            return False

        # 会話文を含む場合は文調保護のため結合しない
        if s1.startswith("「") or s1.startswith("『") or s2.startswith("「") or s2.startswith("『"):
            return False
        if "「" in s1 or "」" in s1 or "「" in s2 or "」" in s2:
            return False

        # 疑問符・感嘆符で終わる文は結合しない
        if re.search(r"[！？!?]$", s1) or re.search(r"[！？!?]$", s2):
            return False

        # 長すぎる場合は結合後の肥大化を防ぐためスキップ
        if len(s1) + len(s2) > limit:
            return False

        # 極端に短い文（体言止め等）は結合不可
        if len(s1) < 4 or len(s2) < 4:
            return False

        return True

    def convert_to_conjunctive(self, sentence: str) -> Optional[str]:
        """Convert a sentence-ending verb/auxiliary into its conjunctive form."""
        s = sentence.strip()

        for pattern, replacement in self.CONJUNCTIVE_MAP:
            if re.search(pattern, s):
                converted = re.sub(pattern, replacement, s)
                if converted != s:
                    return converted
        return None

    def merge_sentences(self, s1: str, s2: str, max_chars: int = 60) -> Optional[str]:
        """Merge two sentences into a single well-formed compound sentence."""
        if not self.can_merge(s1, s2, max_chars=max_chars):
            return None

        conj = self.convert_to_conjunctive(s1)
        if not conj:
            return None

        s2_clean = s2.strip()
        # 結合
        merged = conj + s2_clean
        return merged

    def reduce_consecutive_endings(
        self,
        sentences: List[str],
        max_consecutive: int = 3,
        max_chars: int = 60
    ) -> Tuple[List[str], int]:
        """Scan sentence list and merge when consecutive 'ta' endings exceed threshold."""
        if len(sentences) < 2:
            return sentences, 0

        result: List[str] = []
        i = 0
        merge_count = 0
        consecutive_ta = 0

        while i < len(sentences):
            current = sentences[i].strip()
            if not current:
                i += 1
                continue

            is_ta = bool(re.search(r"[ただ][。]$", current))
            if is_ta:
                consecutive_ta += 1
            else:
                consecutive_ta = 0

            # 閾値に達し、かつ次文が存在する場合に結合を試みる
            if consecutive_ta >= max_consecutive and i + 1 < len(sentences):
                next_s = sentences[i + 1].strip()
                merged = self.merge_sentences(current, next_s, max_chars=max_chars)
                if merged:
                    result.append(merged)
                    merge_count += 1
                    consecutive_ta = 0
                    i += 2  # 2文を消費
                    continue

            result.append(current)
            i += 1

        return result, merge_count
