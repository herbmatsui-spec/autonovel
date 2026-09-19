"""
Dialogue Formatter and Post-processing Pipeline (PLAN_Y3 Step 7-14).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.constraints import CharacterConstraints
from src.narrative.subtext_tokens.expander import TokenExpander

logger = logging.getLogger("narrative.subtext_tokens.formatter")

CLIMAX_EMOTIONS_REGEX = re.compile(r"([^」]*)(爆発|崩壊|決意|覚悟|限界|絶望)([^」]*)(」[。！？]?)")


class DialogueFormatter:
    """Post-processing pipeline formatting and balancing dialogue with stage directions."""

    def __init__(
        self,
        expander: Optional[TokenExpander] = None,
        constraints: Optional[CharacterConstraints] = None,
    ) -> None:
        self.expander = expander or TokenExpander()
        self.constraints = constraints or CharacterConstraints()

    # Step 8: Rule 1 - Normalize punctuation
    @staticmethod
    def normalize_punctuation(text: str) -> str:
        res = text.replace("\r\n", "\n")
        # Unify brackets to Japanese standard
        res = res.replace("“", "「").replace("”", "」")
        # Compress multiple blank lines to at most single empty line
        res = re.sub(r"\n{3,}", "\n\n", res)
        # Unify multiple dots or commas
        res = re.sub(r"([。！？])\1+", r"\1", res)
        res = re.sub(r"……+", "……", res)
        return res.strip()

    # Step 9: Rule 2 - Ensure beat before climax
    @staticmethod
    def ensure_beat_before_climax(text: str) -> str:
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            if CLIMAX_EMOTIONS_REGEX.search(line) and "……" not in line:
                # Insert pause beat before climax word
                line = CLIMAX_EMOTIONS_REGEX.sub(r"\1……\2\3\4", line)
            new_lines.append(line)
        return "\n".join(new_lines)

    # Step 10: Rule 3 - Compress explanatory dialogue
    @staticmethod
    def compress_explanatory_dialogue(text: str) -> str:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        dialogue_indices = [
            i for i, line in enumerate(lines)
            if line.startswith("「") and line.endswith("」")
        ]

        if len(dialogue_indices) >= 3 and dialogue_indices[-1] - dialogue_indices[0] == len(dialogue_indices) - 1:
            # 3 or more consecutive dialogue lines: keep first beat + last line
            last_line = lines[dialogue_indices[-1]]
            new_lines = (
                lines[: dialogue_indices[0]]
                + ["（重苦しい沈黙がその場の空気を凍りつかせる）", last_line]
                + lines[dialogue_indices[-1] + 1 :]
            )
            return "\n".join(new_lines)

        return text

    # Step 11: Rule 4 - Balance dialogue : action ratio
    @staticmethod
    def balance_dialogue_action_ratio(text: str, max_dialogue_ratio: float = 0.7) -> str:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            return text

        dialogue_count = sum(1 for ln in lines if ln.startswith("「"))
        total = len(lines)
        ratio = dialogue_count / total

        if ratio > max_dialogue_ratio and len(lines) >= 3:
            # Insert a stabilizing beat in the middle
            mid = len(lines) // 2
            lines.insert(mid, "（微かに息を整え、手元のカップに視線を落とす）")
            return "\n".join(lines)

        return text

    # Step 12: Rule 5 - Merge consecutive same-speaker dialogue
    @staticmethod
    def merge_consecutive_dialogue(text: str) -> str:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) < 2:
            return text

        new_lines: List[str] = []
        i = 0
        while i < len(lines):
            cur = lines[i]
            if i + 1 < len(lines) and cur.startswith("「") and cur.endswith("」") and lines[i + 1].startswith("「") and lines[i + 1].endswith("」"):
                # Merge into one line with pause beat
                merged = f"「{cur[1:-1]}……{lines[i+1][1:-1]}」"
                new_lines.append(merged)
                i += 2
            else:
                new_lines.append(cur)
                i += 1

        return "\n".join(new_lines)

    # Step 13: Rule 6 - Character speech pattern post-filter
    def apply_speech_filter(self, text: str, character_name: str) -> str:
        if not character_name:
            return text
        return self.constraints.apply_speech_patterns(character_name, text)

    # Step 14: Extension rules 7-12
    @staticmethod
    def apply_extension_rules(text: str) -> str:
        # Rule 7: Clean trailing hyphens or orphan symbols
        res = re.sub(r"——\s*$", "——沈黙が広がる。", text, flags=re.MULTILINE)
        # Rule 8: Ensure quotes are closed properly
        if res.count("「") > res.count("」"):
            res += "」"
        return res

    # Step 7: Master post_process pipeline
    def post_process_dialogue(
        self,
        raw_text: str,
        context: Optional[SubtextContext] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Executes full post-processing pipeline in strict order (Step 7)."""
        # 1. Expand control tokens
        text = self.expander.expand(raw_text, context=context, seed=seed)
        # 2. Normalize punctuation
        text = self.normalize_punctuation(text)
        # 3. Ensure beat before climax
        text = self.ensure_beat_before_climax(text)
        # 4. Compress explanatory dialogue
        text = self.compress_explanatory_dialogue(text)
        # 5. Balance dialogue / action ratio
        text = self.balance_dialogue_action_ratio(text)
        # 6. Merge consecutive same-speaker dialogue
        text = self.merge_consecutive_dialogue(text)
        # 7. Apply character speech patterns
        if context and context.speaker:
            text = self.apply_speech_filter(text, context.speaker)
        # 8. Apply extension formatting rules
        text = self.apply_extension_rules(text)

        return text
