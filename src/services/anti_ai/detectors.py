"""Concrete rule-based detectors for the seven AI categories.

Each detector is a small class that combines:

* a pattern list from :mod:`rule_patterns`
* a config block from :class:`AntiAIConfig`
* a scoring policy tuned for its category

The detectors return :class:`ViolationSpan` lists sorted by
``start``. Aggregating them is the job of the orchestrator
(see :mod:`orchestrator`).
"""

from __future__ import annotations

import re
from typing import Iterable

from src.services.anti_ai.models import (
    AICategory,
    Severity,
    ViolationSpan,
)
from src.services.anti_ai.rule_detector import BaseRuleDetector
from src.services.anti_ai.rule_patterns import (
    DIRECT_EMOTION_PATTERNS,
    GENERIC_VOCABULARY_PATTERN,
    HEDGING_PATTERNS,
    SAME_STRUCTURE_TAILS,
    TEMPLATE_PHRASES,
    TRANSITION_OVERUSE_PATTERNS,
    UNIFORM_PARAGRAPH_LENGTH_TOLERANCE,
    UNIFORM_PARAGRAPH_MIN_PARAGRAPHS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _split_sentences(text: str) -> list[tuple[int, int, str]]:
    """Split ``text`` into (start, end, sentence) triples.

    The end offset is exclusive and includes the terminating
    punctuation if present. Used by detectors that need to look
    at adjacent sentences (e.g. SAME_STRUCTURE).
    """
    out: list[tuple[int, int, str]] = []
    start = 0
    for i, ch in enumerate(text):
        if ch in ("。", "！", "?", "？", "!", "\n"):
            end = i + 1
            sentence = text[start:end].strip()
            if sentence:
                out.append((start, end, sentence))
            start = end
    tail = text[start:].strip()
    if tail:
        out.append((start, start + len(tail), tail))
    return out


def _split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    start = 0
    parts = re.split(r"\n\s*\n", text)
    cursor = 0
    for part in parts:
        idx = text.find(part, cursor)
        if idx < 0:
            continue
        end = idx + len(part)
        out.append((idx, end, part))
        cursor = end
    return out


# ---------------------------------------------------------------------------
# TRANSITION_OVERUSE
# ---------------------------------------------------------------------------
class TransitionOveruseDetector(BaseRuleDetector):
    """Detects overuse of scene-glue transition words at sentence start."""

    category = AICategory.TRANSITION_OVERUSE

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled():
            return []
        if not text or not text.strip():
            return []

        violations: list[ViolationSpan] = []
        for pattern in TRANSITION_OVERUSE_PATTERNS:
            for m in pattern.finditer(text):
                violations.append(self._make_violation(m.start(), m.end(), m.group(0).strip()))

        # Score by density: how many transitions per sentence?
        sentences = _split_sentences(text)
        if not sentences:
            return sorted(violations, key=lambda v: v.start)

        unique_starts = {v.start for v in violations}
        density = len(unique_starts) / max(len(sentences), 1)

        # Configurable threshold (default 0.33)
        threshold = 0.33
        if self.config is not None:
            threshold = self.config.detectors.TRANSITION_OVERUSE.density_threshold

        if density < threshold:
            # Below threshold → only flag the *most* egregious match as info.
            return [v for v in violations if v.start in unique_starts][: max(0, len(unique_starts) - 1)]

        return sorted(violations, key=lambda v: v.start)

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        sentences = _split_sentences(text)
        if not sentences:
            return 100.0
        density = len({v.start for v in violations}) / max(len(sentences), 1)
        threshold = 0.33
        if self.config is not None:
            threshold = self.config.detectors.TRANSITION_OVERUSE.density_threshold
        # density 0 -> 100, density == threshold -> 60, density == 2*threshold -> 0
        if density <= 0:
            return 100.0
        score = 100.0 - 100.0 * (density / (threshold * 2.0))
        return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# SAME_STRUCTURE
# ---------------------------------------------------------------------------
class SameStructureDetector(BaseRuleDetector):
    """Detects 3+ consecutive sentences ending with the same tail."""

    category = AICategory.SAME_STRUCTURE

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        consecutive_count = 3
        if self.config is not None:
            consecutive_count = self.config.detectors.SAME_STRUCTURE.consecutive_count

        sentences = _split_sentences(text)
        if len(sentences) < consecutive_count:
            return []

        def _tail(sentence: str) -> str:
            for tail_pat in SAME_STRUCTURE_TAILS:
                tm = tail_pat.search(sentence)
                if tm:
                    return tm.group(0).strip()
            return ""

        violations: list[ViolationSpan] = []
        i = 0
        while i < len(sentences):
            t = _tail(sentences[i][2])
            if not t:
                i += 1
                continue
            j = i + 1
            while j < len(sentences) and _tail(sentences[j][2]) == t:
                j += 1
            run_length = j - i
            if run_length >= consecutive_count:
                # Flag the whole run except the first sentence (one is fine).
                for k in range(i + 1, j):
                    s_start, s_end, _ = sentences[k]
                    violations.append(
                        self._make_violation(
                            s_start, s_end, text[s_start:s_end], severity=Severity.HIGH
                        )
                    )
            i = j
        return violations

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        sentences = _split_sentences(text)
        if not sentences:
            return 100.0
        consecutive_count = 3
        if self.config is not None:
            consecutive_count = self.config.detectors.SAME_STRUCTURE.consecutive_count
        # Ratio of flagged sentences to total
        ratio = len(violations) / max(len(sentences), 1)
        if ratio == 0:
            return 100.0
        # 0.05 ratio (≈1 in 20 sentences) -> 90
        # 0.20 ratio -> 40
        score = 100.0 - (ratio * 300.0)
        return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# DIRECT_EMOTION
# ---------------------------------------------------------------------------
class DirectEmotionDetector(BaseRuleDetector):
    """Detects overuse of explicit first-person internal-monologue verbs."""

    category = AICategory.DIRECT_EMOTION

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        per_paragraph_limit = 2
        if self.config is not None:
            per_paragraph_limit = self.config.detectors.DIRECT_EMOTION.per_paragraph_limit

        violations: list[ViolationSpan] = []
        for p_start, p_end, paragraph in _split_paragraphs(text):
            matches: list[re.Match[str]] = []
            for pat in DIRECT_EMOTION_PATTERNS:
                matches.extend(pat.finditer(paragraph))
            matches.sort(key=lambda m: m.start())
            if len(matches) > per_paragraph_limit:
                for m in matches[per_paragraph_limit:]:
                    violations.append(
                        self._make_violation(
                            p_start + m.start(), p_start + m.end(), m.group(0)
                        )
                    )
        return violations

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        paragraphs = _split_paragraphs(text)
        if not paragraphs:
            return 100.0
        ratio = len(violations) / max(len(paragraphs), 1)
        if ratio == 0:
            return 100.0
        return max(0.0, min(100.0, 100.0 - ratio * 100.0))


# ---------------------------------------------------------------------------
# HEDGING_PATTERNS
# ---------------------------------------------------------------------------
class HedgingPatternsDetector(BaseRuleDetector):
    """Detects epistemic hedging markers typical of LLM prose."""

    category = AICategory.HEDGING_PATTERNS

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        sentences = _split_sentences(text)
        if not sentences:
            return []

        violations: list[ViolationSpan] = []
        for s_start, s_end, sentence in sentences:
            for pat in HEDGING_PATTERNS:
                for m in pat.finditer(sentence):
                    violations.append(
                        self._make_violation(
                            s_start + m.start(), s_start + m.end(), m.group(0)
                        )
                    )
        # Sort by start offset to guarantee stable ordering.
        violations.sort(key=lambda v: v.start)
        return violations

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        sentences = _split_sentences(text)
        if not sentences:
            return 100.0
        density = len(violations) / max(len(sentences), 1)
        threshold = 0.10
        if self.config is not None:
            threshold = self.config.detectors.HEDGING_PATTERNS.density_threshold
        if density <= 0:
            return 100.0
        # density / (2*threshold) maps to 100 -> 0
        score = 100.0 - 100.0 * (density / (threshold * 2.0))
        return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# TEMPLATE_PHRASES
# ---------------------------------------------------------------------------
class TemplatePhrasesDetector(BaseRuleDetector):
    """Detects essay/report-style connective template phrases."""

    category = AICategory.TEMPLATE_PHRASES

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        min_matches = 1
        if self.config is not None:
            min_matches = self.config.detectors.TEMPLATE_PHRASES.min_matches

        violations: list[ViolationSpan] = []
        for pat in TEMPLATE_PHRASES:
            for m in pat.finditer(text):
                violations.append(self._make_violation(m.start(), m.end(), m.group(0)))
        violations.sort(key=lambda v: v.start)
        # If the user requires N matches before flagging, trim.
        if min_matches > 1 and len(violations) < min_matches:
            return []
        return violations

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        if not violations:
            return 100.0
        density = (len(violations) * 1000.0) / max(len(text), 1)
        # 0.5 per 1000 -> 100, 5 per 1000 -> 0
        score = 100.0 - (density * 20.0)
        return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# UNIFORM_PARAGRAPH
# ---------------------------------------------------------------------------
class UniformParagraphDetector(BaseRuleDetector):
    """Detects 3+ paragraphs of suspiciously uniform length."""

    category = AICategory.UNIFORM_PARAGRAPH

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        min_paragraphs = UNIFORM_PARAGRAPH_MIN_PARAGRAPHS
        tolerance = UNIFORM_PARAGRAPH_LENGTH_TOLERANCE
        if self.config is not None:
            min_paragraphs = self.config.detectors.UNIFORM_PARAGRAPH.min_paragraphs
            tolerance = self.config.detectors.UNIFORM_PARAGRAPH.length_tolerance

        paragraphs = _split_paragraphs(text)
        if len(paragraphs) < min_paragraphs:
            return []

        lengths = [len(p[2]) for p in paragraphs]
        violations: list[ViolationSpan] = []
        # Sliding window of min_paragraphs
        for i in range(0, len(paragraphs) - min_paragraphs + 1):
            window = lengths[i : i + min_paragraphs]
            if max(window) - min(window) <= tolerance:
                # All paragraphs in the window are too uniform.
                for k in range(i, i + min_paragraphs):
                    p_start, p_end, _ = paragraphs[k]
                    violations.append(
                        self._make_violation(p_start, p_end, text[p_start:p_end])
                    )
        # Deduplicate while preserving order (use set on (start,end))
        seen: set[tuple[int, int]] = set()
        deduped: list[ViolationSpan] = []
        for v in violations:
            key = (v.start, v.end)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(v)
        return deduped

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        paragraphs = _split_paragraphs(text)
        if not paragraphs:
            return 100.0
        ratio = len(violations) / max(len(paragraphs), 1)
        if ratio == 0:
            return 100.0
        return max(0.0, min(100.0, 100.0 - ratio * 80.0))


# ---------------------------------------------------------------------------
# GENERIC_VOCABULARY
# ---------------------------------------------------------------------------
class GenericVocabularyDetector(BaseRuleDetector):
    """Detects LLM-typical abstract adjectives."""

    category = AICategory.GENERIC_VOCABULARY

    def detect(self, text: str) -> list[ViolationSpan]:
        if not self._is_enabled() or not text or not text.strip():
            return []

        violations: list[ViolationSpan] = []
        for m in GENERIC_VOCABULARY_PATTERN.finditer(text):
            violations.append(self._make_violation(m.start(), m.end(), m.group(0)))
        return violations

    def score_from_violations(self, text: str, violations: list[ViolationSpan]) -> float:
        if not text:
            return 100.0
        if not violations:
            return 100.0
        density = (len(violations) * 1000.0) / max(len(text), 1)
        density_per_1000 = 5.0
        if self.config is not None:
            density_per_1000 = self.config.detectors.GENERIC_VOCABULARY.density_per_1000
        if density <= 0:
            return 100.0
        # density == density_per_1000 -> 60
        # density == 2*density_per_1000 -> 0
        score = 100.0 - 100.0 * (density / (density_per_1000 * 2.0))
        return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
RULE_DETECTORS: dict[AICategory, type[BaseRuleDetector]] = {
    AICategory.TRANSITION_OVERUSE: TransitionOveruseDetector,
    AICategory.SAME_STRUCTURE: SameStructureDetector,
    AICategory.DIRECT_EMOTION: DirectEmotionDetector,
    AICategory.HEDGING_PATTERNS: HedgingPatternsDetector,
    AICategory.TEMPLATE_PHRASES: TemplatePhrasesDetector,
    AICategory.UNIFORM_PARAGRAPH: UniformParagraphDetector,
    AICategory.GENERIC_VOCABULARY: GenericVocabularyDetector,
}


__all__ = [
    "TransitionOveruseDetector",
    "SameStructureDetector",
    "DirectEmotionDetector",
    "HedgingPatternsDetector",
    "TemplatePhrasesDetector",
    "UniformParagraphDetector",
    "GenericVocabularyDetector",
    "RULE_DETECTORS",
    "_split_sentences",
    "_split_paragraphs",
]
