"""Violation Span Extractor for localized cadence reformation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class TargetSpan:
    """Localized text window containing cadence violations with surrounding context."""
    start_sentence_idx: int
    end_sentence_idx: int
    target_sentences: List[str]
    preceding_context: str = ""
    following_context: str = ""
    violation_type: str = "consecutive_ta"

    @property
    def target_text(self) -> str:
        return "".join(self.target_sentences)

    @property
    def window_text(self) -> str:
        parts = []
        if self.preceding_context:
            parts.append(f"[直前文脈]: {self.preceding_context}")
        parts.append(f"[改善対象]: {self.target_text}")
        if self.following_context:
            parts.append(f"[直後文脈]: {self.following_context}")
        return "\n".join(parts)


class ViolationSpanExtractor:
    """Extracts minimal bounding spans of consecutive cadence violations."""

    def __init__(self, max_consecutive: int = 3) -> None:
        self.max_consecutive = max_consecutive

    def extract_spans(self, sentences: List[str]) -> List[TargetSpan]:
        """Find all violation spans where consecutive 'ta' endings reach the threshold."""
        if len(sentences) < self.max_consecutive:
            return []

        spans: List[TargetSpan] = []
        consecutive_indices: List[int] = []

        for idx, sentence in enumerate(sentences):
            s = sentence.strip()
            if not s or s.startswith("「") or s.startswith("『"):
                consecutive_indices.clear()
                continue

            is_ta = bool(re.search(r"[ただ][。]$", s))
            if is_ta:
                consecutive_indices.append(idx)
                if len(consecutive_indices) >= self.max_consecutive:
                    # 違反スパンを生成
                    start_idx = consecutive_indices[0]
                    end_idx = consecutive_indices[-1]

                    prec = sentences[start_idx - 1].strip() if start_idx > 0 else ""
                    foll = sentences[end_idx + 1].strip() if end_idx + 1 < len(sentences) else ""

                    spans.append(TargetSpan(
                        start_sentence_idx=start_idx,
                        end_sentence_idx=end_idx,
                        target_sentences=sentences[start_idx:end_idx + 1],
                        preceding_context=prec,
                        following_context=foll,
                        violation_type="consecutive_ta"
                    ))
                    # スパンを消費したのでリセット
                    consecutive_indices.clear()
            else:
                consecutive_indices.clear()

        return spans

    def splice_span(
        self,
        sentences: List[str],
        span: TargetSpan,
        refined_text: str
    ) -> List[str]:
        """Splice refined text back into the sentence list at the exact span location."""
        refined_clean = refined_text.strip()
        if not refined_clean:
            return sentences

        # 句点で文分割してリスト化
        refined_sentences = [
            s.strip() for s in re.split(r"(?<=[。！？!?])", refined_clean) if s.strip()
        ]
        if not refined_sentences:
            refined_sentences = [refined_clean]

        prefix = sentences[:span.start_sentence_idx]
        suffix = sentences[span.end_sentence_idx + 1:]

        return prefix + refined_sentences + suffix
