"""Windowing and Section Extraction for Specialist Auditors.

Provides NovelSectionExtractor to split long novel drafts into contextual windows
(e.g., Opening, Ending, Four Narrative Sections / Kishotenketsu) snapping cleanly
to sentence boundaries (句点 '。！？' or newline) instead of hard 4000-char truncation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NovelSection:
    """Represents an extracted contextual section/window from a novel draft."""
    name: str  # e.g., "opening", "ending", "ki", "sho", "ten", "ketsu", "section_1"
    text: str
    start_pos: int
    end_pos: int
    char_count: int = field(init=False)
    relative_start: float = 0.0  # 0.0 to 1.0
    relative_end: float = 0.0  # 0.0 to 1.0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)

    def __str__(self) -> str:
        return self.text

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "text": self.text,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "char_count": self.char_count,
            "relative_start": self.relative_start,
            "relative_end": self.relative_end,
        }


class NovelSectionExtractor:
    """Extracts narrative windows (opening, ending, kishotenketsu sections)
    with boundary snapping to prevent sentence cutting.
    """

    SENTENCE_END_PATTERN = re.compile(r"[。！？!?\n]+")

    def __init__(self) -> None:
        pass

    def _snap_forward(self, text: str, target_idx: int, max_idx: int) -> int:
        """Find the nearest sentence end at or before target_idx.
        If none found before target_idx, search forward up to max_idx.
        """
        if target_idx <= 0:
            return 0
        if target_idx >= len(text):
            return len(text)

        # 1. Search backward from target_idx for sentence end
        search_region = text[:target_idx]
        matches = list(self.SENTENCE_END_PATTERN.finditer(search_region))
        if matches:
            last_match = matches[-1]
            return last_match.end()

        # 2. If no sentence end before target_idx, look forward up to max_idx
        forward_region = text[target_idx:max_idx]
        m = self.SENTENCE_END_PATTERN.search(forward_region)
        if m:
            return target_idx + m.end()

        # Fallback to target_idx
        return target_idx

    def _snap_backward(self, text: str, target_idx: int, min_idx: int) -> int:
        """Find the nearest sentence end at or around target_idx for beginning a section.
        The returned index is the start of the next sentence (right after a sentence end).
        """
        if target_idx <= 0:
            return 0
        if target_idx >= len(text):
            return len(text)

        # 1. Look forward from target_idx for a sentence end, and start after it
        search_region = text[target_idx:]
        m = self.SENTENCE_END_PATTERN.search(search_region)
        if m and (target_idx + m.end() <= len(text)):
            return target_idx + m.end()

        # 2. Look backward down to min_idx
        backward_region = text[min_idx:target_idx]
        matches = list(self.SENTENCE_END_PATTERN.finditer(backward_region))
        if matches:
            return min_idx + matches[-1].end()

        return target_idx

    def extract_opening(self, text: str, max_chars: int = 1500) -> str:
        """Extract opening hook section, snapping cleanly to sentence boundary.
        Guaranteed to be <= max_chars unless first sentence itself exceeds max_chars.
        """
        if not text:
            return ""
        if len(text) <= max_chars:
            return text

        # Find best sentence end near max_chars without exceeding it
        sub = text[:max_chars]
        matches = list(self.SENTENCE_END_PATTERN.finditer(sub))
        if matches:
            # Cut at the end of the last sentence within max_chars
            cut_idx = matches[-1].end()
            # If the cut is reasonable (e.g. at least 40% of max_chars)
            if cut_idx >= max_chars * 0.4:
                return text[:cut_idx]

        # If no sentence break found or too early, hard-cut at max_chars
        return text[:max_chars]

    def extract_ending(self, text: str, max_chars: int = 1500) -> str:
        """Extract ending cliffhanger section, snapping cleanly to sentence boundary
        near the start of the section.
        """
        if not text:
            return ""
        if len(text) <= max_chars:
            return text

        start_candidate = len(text) - max_chars
        # Search for a sentence end around start_candidate so the ending section begins
        # at the start of a complete sentence.
        search_window = text[start_candidate:start_candidate + min(300, max_chars // 2)]
        m = self.SENTENCE_END_PATTERN.search(search_window)
        if m:
            clean_start = start_candidate + m.end()
            return text[clean_start:]

        # Fallback to exact slice
        return text[start_candidate:]

    def extract_four_sections(
        self,
        text: str,
        section_chars: int = 800,
    ) -> list[NovelSection]:
        """Extract 4 representative sections (起・承・転・結) evenly distributed
        across the draft, snapping each window to sentence boundaries.
        """
        if not text:
            return [
                NovelSection("ki", "", 0, 0, 0.0, 0.0),
                NovelSection("sho", "", 0, 0, 0.0, 0.0),
                NovelSection("ten", "", 0, 0, 0.0, 0.0),
                NovelSection("ketsu", "", 0, 0, 0.0, 0.0),
            ]

        total_len = len(text)
        section_names = ["ki", "sho", "ten", "ketsu"]

        # If total text fits comfortably within 4 * section_chars,
        # split text cleanly into 4 sequential parts at sentence boundaries.
        if total_len <= section_chars * 4:
            quarter = total_len / 4.0
            split_points = [0]
            for i in range(1, 4):
                raw_idx = int(i * quarter)
                snapped_idx = self._snap_forward(text, raw_idx, int((i + 0.5) * quarter))
                # Ensure monotonic progression
                if snapped_idx <= split_points[-1]:
                    snapped_idx = raw_idx
                split_points.append(snapped_idx)
            split_points.append(total_len)

            sections: list[NovelSection] = []
            for i in range(4):
                sp = split_points[i]
                ep = split_points[i + 1]
                sec_text = text[sp:ep].strip()
                sections.append(
                    NovelSection(
                        name=section_names[i],
                        text=sec_text,
                        start_pos=sp,
                        end_pos=ep,
                        relative_start=round(sp / total_len, 3),
                        relative_end=round(ep / total_len, 3),
                    )
                )
            return sections

        # Long text: sample 4 windows centered around 12.5%, 37.5%, 62.5%, 87.5%
        # with sentence boundary snapping.
        centers = [
            0.125 * total_len,
            0.375 * total_len,
            0.625 * total_len,
            0.875 * total_len,
        ]

        sections = []
        for i, center in enumerate(centers):
            name = section_names[i]
            ideal_start = max(0, int(center - section_chars / 2))
            ideal_end = min(total_len, ideal_start + section_chars)

            if i == 0:
                # First section (起): start from beginning
                sec_text = self.extract_opening(text, section_chars)
                sp = 0
                ep = len(sec_text)
            elif i == 3:
                # Last section (結): take clean ending
                sec_text = self.extract_ending(text, section_chars)
                sp = total_len - len(sec_text)
                ep = total_len
            else:
                # Middle sections (承, 転): snap start and end to sentence boundaries
                snapped_start = self._snap_backward(
                    text,
                    ideal_start,
                    min_idx=max(0, ideal_start - 200),
                )
                snapped_end = self._snap_forward(
                    text,
                    ideal_end,
                    max_idx=min(total_len, ideal_end + 200),
                )
                if snapped_end <= snapped_start:
                    snapped_start = ideal_start
                    snapped_end = ideal_end

                sec_text = text[snapped_start:snapped_end].strip()
                sp = snapped_start
                ep = snapped_end

            sections.append(
                NovelSection(
                    name=name,
                    text=sec_text,
                    start_pos=sp,
                    end_pos=ep,
                    relative_start=round(sp / total_len, 3),
                    relative_end=round(ep / total_len, 3),
                )
            )

        return sections

    def extract_relevant_context(
        self,
        text: str,
        keywords: list[str],
        max_chars: int = 2500,
    ) -> str:
        """Extract sections of text that are most relevant to the given keywords.
        Splits text by paragraphs/sentences, scores them by keyword matches,
        and joins top matching contiguous or key windows up to max_chars.
        If no keywords match or text is short, returns text[:max_chars].
        """
        if not text or len(text) <= max_chars:
            return text

        if not keywords:
            return self.extract_opening(text, max_chars)

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return text[:max_chars]

        # Score paragraphs
        scored_paras: list[tuple[int, int, str]] = []  # (score, index, text)
        for i, para in enumerate(paragraphs):
            score = sum(1 for kw in keywords if kw and kw in para)
            scored_paras.append((score, i, para))

        # Find best cluster of paragraphs around highest score
        max_score = max(p[0] for p in scored_paras)
        if max_score == 0:
            # Fallback to opening + ending
            half = max_chars // 2
            op = self.extract_opening(text, half)
            ed = self.extract_ending(text, half)
            return f"{op}\n\n[...中略...]\n\n{ed}"

        # Get the top scoring paragraph index
        best_idx = max(range(len(scored_paras)), key=lambda i: scored_paras[i][0])

        # Expand around best_idx
        start_idx = best_idx
        end_idx = best_idx + 1
        current_len = len(paragraphs[best_idx])

        while current_len < max_chars:
            expanded = False
            # Try expand forward
            if end_idx < len(paragraphs):
                next_len = len(paragraphs[end_idx]) + 1
                if current_len + next_len <= max_chars:
                    current_len += next_len
                    end_idx += 1
                    expanded = True
            # Try expand backward
            if start_idx > 0:
                prev_len = len(paragraphs[start_idx - 1]) + 1
                if current_len + prev_len <= max_chars:
                    current_len += prev_len
                    start_idx -= 1
                    expanded = True
            if not expanded:
                break

        selected_paras = paragraphs[start_idx:end_idx]
        result = "\n\n".join(selected_paras)

        prefix = "[...前略...]\n\n" if start_idx > 0 else ""
        suffix = "\n\n[...後略...]" if end_idx < len(paragraphs) else ""
        return f"{prefix}{result}{suffix}"
