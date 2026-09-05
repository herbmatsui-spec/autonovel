"""Concrete correctors for the seven AI-fingerprint categories.

Each corrector pairs with its detector (same category). We use
*conservative* string-level rewrites so the corrector is safe to
run on a CPU-only machine without an LLM.
"""

from __future__ import annotations

import re
from collections import defaultdict

from src.services.anti_ai.corrector import BaseCorrector, _apply_replacements
from src.services.anti_ai.models import AICategory, ViolationSpan


# ---------------------------------------------------------------------------
# TRANSITION_OVERUSE
# ---------------------------------------------------------------------------
class TransitionOveruseCorrector(BaseCorrector):
    """Remove or replace the *redundant* filler transitions.

    Strategy: of the violations that the detector flagged, keep the
    first one (it can be a real narrative transition) and rewrite
    or drop the rest. We round-robin through a small set of natural
    alternatives so consecutive rewritten sentences do not all
    share the same opener.
    """

    category = AICategory.TRANSITION_OVERUSE

    # Drop-targets: "しかし" / "また" can almost always be removed
    # without breaking the sentence.
    _DROPPABLE: dict[str, str] = {
        "しかし": "",
        "また": "",
        "なお": "",
        "しかも": "",
    }

    # Replacement pool for things we keep but want to vary
    _VARIANTS: dict[str, list[str]] = {
        "しかし": ["それでも", "それでもやはり"],
        "さらに": ["そして", "その上で"],
        "また": ["その折も", ""],
        "ところで": ["唐突だが", ""],
        "そもそも": ["本来なら", "事の起こりは"],
    }

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        if not violations:
            return []
        # Keep the first violation untouched, rewrite the rest.
        edits: list[tuple[int, int, str]] = []
        variant_counters: dict[str, int] = defaultdict(int)
        for idx, v in enumerate(violations):
            if idx == 0:
                continue
            original = v.matched_text.strip()
            if original in self._DROPPABLE:
                # When dropping, also eat the trailing「、」or whitespace
                # so we don't leave a sentence that starts with「、」.
                end = v.end
                while end < len(text) and text[end] in ("、", " ", "　"):
                    end += 1
                edits.append((v.start, end, ""))
                continue
            variants = self._VARIANTS.get(original)
            if variants:
                i = variant_counters[original] % len(variants)
                variant_counters[original] += 1
                replacement = variants[i]
                if replacement:
                    edits.append((v.start, v.end, replacement))
                else:
                    # Drop the variant too, same trailing cleanup
                    end = v.end
                    while end < len(text) and text[end] in ("、", " ", "　"):
                        end += 1
                    edits.append((v.start, end, ""))
                continue
            # Unknown transition → drop, it's the safest move.
            end = v.end
            while end < len(text) and text[end] in ("、", " ", "　"):
                end += 1
            edits.append((v.start, end, ""))
        return edits


# ---------------------------------------------------------------------------
# SAME_STRUCTURE
# ---------------------------------------------------------------------------
class SameStructureCorrector(BaseCorrector):
    """Diversify sentence endings that have piled up."""

    category = AICategory.SAME_STRUCTURE

    # Map of "offending tail" -> list of alternative endings.
    # The corrector picks the next one in round-robin order to keep
    # the variation natural.
    _ALTERNATIVE_ENDS: dict[str, list[str]] = {
        "だった。": ["だった。", "であった。", "だ。", "だったのだ。"],
        "であった。": ["だった。", "であった。", "だ。"],
        "ました。": ["た。", "たのだ。", "たのであった。"],
        "です。": ["だ。", "である。", "のことだ。"],
        "ます。": ["る。", "た。", "よう。"],
        "った。": ["った。", "てみせた。", "ってみせた。", "ったはずだった。"],
        "いた。": ["いた。", "ていた。", "いていた。"],
    }

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        edits: list[tuple[int, int, str]] = []
        seen_tail: dict[str, int] = defaultdict(int)
        for v in violations:
            sentence = v.matched_text
            # Find the tail in this sentence.
            tail_match = re.search(r"[。\n]?([だで]った|であった|ました|です|ます|[、]?った|[、]?いた)[。\n]?$", sentence)
            if not tail_match:
                continue
            tail = tail_match.group(0)
            # Canonical key (without trailing punctuation variation)
            key = tail_match.group(1) + "。" if not tail.endswith("。") else tail_match.group(1) + "。"
            alts = self._ALTERNATIVE_ENDS.get(key)
            if not alts:
                # Try without the trailing 。
                key2 = key.rstrip("。")
                alts = self._ALTERNATIVE_ENDS.get(key2 + "。")
                if not alts:
                    continue
                key = key2 + "。"
            # Pick a different ending.
            i = seen_tail[key] % len(alts)
            seen_tail[key] += 1
            new_end = alts[i]
            # Replace the tail in the sentence text (preserving leading chars).
            old_end = tail_match.group(0)
            # Compute offsets within the full text
            tail_start = v.start + (len(sentence) - len(old_end))
            tail_end = v.start + len(sentence)
            new_sentence = sentence[: len(sentence) - len(old_end)] + new_end
            edits.append((v.start, v.end, new_sentence))
        return edits


# ---------------------------------------------------------------------------
# DIRECT_EMOTION
# ---------------------------------------------------------------------------
class DirectEmotionCorrector(BaseCorrector):
    """Rewrite explicit internal-monologue verbs into five-sense cues.

    Strategy: replace「〜と思った」etc. with a generic physical
    expression that conveys the emotion without naming it. We keep
    the sentence structure intact.
    """

    category = AICategory.DIRECT_EMOTION

    _REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"と(思っ|感じ|考え)た[。\n]"), "胸がざわついた。"),
        (re.compile(r"と思えた[。\n]"), "胸がざわついた。"),
        (re.compile(r"と思わずに(?:は)?いられな[いか]"), "胸が締めつけられた"),
    ]

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        edits: list[tuple[int, int, str]] = []
        for v in violations:
            matched = v.matched_text
            for pattern, replacement in self._REPLACEMENTS:
                if pattern.fullmatch(matched):
                    edits.append((v.start, v.end, replacement))
                    break
            else:
                if "胸の中" in matched or "心の中" in matched:
                    edits.append((v.start, v.end, "胸の鼓動が速まった。"))
        return edits


# ---------------------------------------------------------------------------
# HEDGING_PATTERNS
# ---------------------------------------------------------------------------
class HedgingPatternsCorrector(BaseCorrector):
    """Replace epistemic hedging with more direct assertions.

    Strategy: most hedging patterns are dropped or replaced with
    more assertive phrasing. Round-robin through alternatives.
    """

    category = AICategory.HEDGING_PATTERNS

    _DIRECT_ASSERTIONS: dict[str, list[str]] = {
        "かもしれません": ["だろう", "だ"],
        "かも": ["だろう", "だ"],
        "可能性": ["事実", ""],
        "考えられ": ["確か", ""],
        "思われ": ["確か", ""],
        "言える": ["言う", ""],
        "思います": ["と思う", ""],
        "思われます": ["と思う", ""],
        "考えられます": ["と思う", ""],
        "言えるでしょう": ["と言える", ""],
        "ではないでしょうか": ["だ", ""],
        "だろう": ["だ", ""],
        "でしょう": ["だ", ""],
        "はず": ["だ", ""],
        "おそらく": ["確かに", "確かに"],
        "たぶん": ["確かに", "確かに"],
        "きっと": ["確かに", "確かに"],
    }

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        edits: list[tuple[int, int, str]] = []
        counters: dict[str, int] = defaultdict(int)
        for v in violations:
            original = v.matched_text.strip()
            replacements = self._DIRECT_ASSERTIONS.get(original)
            if replacements:
                i = counters[original] % len(replacements)
                counters[original] += 1
                replacement = replacements[i]
                if replacement:
                    edits.append((v.start, v.end, replacement))
            else:
                for key, alts in self._DIRECT_ASSERTIONS.items():
                    if key in original:
                        i = counters[key] % len(alts)
                        counters[key] += 1
                        replacement = alts[i]
                        if replacement:
                            edits.append((v.start, v.end, replacement))
                        break
        return edits


# ---------------------------------------------------------------------------
# TEMPLATE_PHRASES
# ---------------------------------------------------------------------------
class TemplatePhrasesCorrector(BaseCorrector):
    """Remove or rewrite essay/report-style template phrases.

    Strategy: these phrases are dropped entirely as they break
    narrative flow. They are characteristic of LLM-generated
    expository prose.
    """

    category = AICategory.TEMPLATE_PHRASES

    _DROP_PATTERNS: set[str] = {
        "重要な",
        "大切な",
        "注目すべき",
        "注目したい",
        "結論として",
        "結論すると",
        "結論すれば",
        "まず第一に",
        "まず最初に",
        "次に、",
        "次に考え",
        "最後に、",
        "最後にまとめると",
        "最後に触れて",
        "総括する",
        "総括すると",
        "総括すれば",
        "要約する",
        "要約すると",
        "要約すれば",
        "以下、",
        "以下のように",
        "以下の",
        "以上、",
        "以上のように",
        "上記の",
    }

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        edits: list[tuple[int, int, str]] = []
        for v in violations:
            original = v.matched_text.strip()
            if original in self._DROP_PATTERNS:
                edits.append((v.start, v.end, ""))
            else:
                for drop in self._DROP_PATTERNS:
                    if drop in original:
                        edits.append((v.start, v.end, ""))
                        break
        return edits


# ---------------------------------------------------------------------------
# UNIFORM_PARAGRAPH
# ---------------------------------------------------------------------------
class UniformParagraphCorrector(BaseCorrector):
    """Diversify paragraph lengths that have become too uniform.

    Strategy: this is a structural issue that cannot be fully
    corrected with simple string replacements. We flag the issue
    for human review but do not attempt auto-correction.
    """

    category = AICategory.UNIFORM_PARAGRAPH

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        return []


# ---------------------------------------------------------------------------
# GENERIC_VOCABULARY
# ---------------------------------------------------------------------------
class GenericVocabularyCorrector(BaseCorrector):
    """Replace generic/abstract adjectives with more concrete descriptors.

    Strategy: round-robin through concrete alternatives. Some generic
    terms like「素晴らしい」can be replaced with scene-specific verbs
    or dropped entirely.
    """

    category = AICategory.GENERIC_VOCABULARY

    _CONCRETE_ALTERNATIVES: dict[str, list[str]] = {
        "素晴らしい": ["見事だった", "目覚ましい", ""],
        "興味深い": ["目を引いた", ""],
        "多様な": ["幅広い", "様々な"],
        "重要な": ["主要な", "大きな", ""],
        "深刻な": ["重い", ""],
        "顕著な": ["著しい", ""],
        "顕著": ["著しく", ""],
        "様々な": ["方方面面の", ""],
        "多種多様な": ["あらゆる", ""],
        "有意義な": ["得るもののある", ""],
        "価値ある": ["価値のある", ""],
        "不可欠な": ["欠かすことのできない", ""],
        "本質的な": ["根底にある", ""],
        "根本的な": ["基本的な", ""],
        "包括的な": ["広範囲の", ""],
        "総合的な": ["全体の", ""],
        "全体的な": ["全体の", ""],
        "一般的な": [" обычных", ""],
        "広範な": ["広い", ""],
        "巨大な": ["大きな", ""],
        "豊富な": ["多くの", ""],
    }

    def _build_replacements(
        self, text: str, violations: list[ViolationSpan]
    ) -> list[tuple[int, int, str]]:
        edits: list[tuple[int, int, str]] = []
        counters: dict[str, int] = defaultdict(int)
        for v in violations:
            original = v.matched_text.strip()
            alts = self._CONCRETE_ALTERNATIVES.get(original)
            if alts:
                i = counters[original] % len(alts)
                counters[original] += 1
                replacement = alts[i]
                if replacement:
                    edits.append((v.start, v.end, replacement))
        return edits


__all__ = [
    "TransitionOveruseCorrector",
    "SameStructureCorrector",
    "DirectEmotionCorrector",
    "HedgingPatternsCorrector",
    "TemplatePhrasesCorrector",
    "UniformParagraphCorrector",
    "GenericVocabularyCorrector",
]
