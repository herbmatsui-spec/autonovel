"""Rule-based detection patterns for all 7 AI fingerprint categories.

Each entry is a list of regex patterns applied with ``re.finditer``
against the source text. Patterns are deliberately conservative
(short, anchored) so that false positives stay manageable on
classical Japanese prose. The detectors themselves decide how to
weight and threshold the matches — this module only stores the
raw patterns.
"""

from __future__ import annotations

import re
from typing import Pattern

# ---------------------------------------------------------------------------
# TRANSITION_OVERUSE: filler conjunctions used as scene/paragraph glue.
# Detected at the *start* of sentences. Density is computed by the
# detector, not by raw match count.
#
# Patterns match anywhere a sentence can start (after punctuation,
# whitespace or beginning of text). We do NOT use the ``^`` anchor
# because that would only catch the very first sentence of the text;
# we use a leading lookbehind for the sentence boundary.
# The trailing character class was removed because re.findall /
# finditer greedy match would otherwise consume a real sentence
# character that we don't want to eat.
# ---------------------------------------------------------------------------
_TRANSITION_BOUNDARY = r"(?:^|(?<=[。\n!?！？]))[\s　]*"
TRANSITION_OVERUSE_PATTERNS: list[Pattern[str]] = [
    re.compile(_TRANSITION_BOUNDARY + r"しかし(?=[、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"さらに(?=[、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"また(?=[、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"なお(?=[、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"ところで(?=[、、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"しかも(?=[、。\s])"),
    re.compile(_TRANSITION_BOUNDARY + r"一方(?=[、で])"),
    re.compile(_TRANSITION_BOUNDARY + r"そもそも(?=[、。\s])"),
]

# ---------------------------------------------------------------------------
# SAME_STRUCTURE: 3+ consecutive sentences sharing the same sentence-end
# Captured via a post-processing check; this module only provides the
# tail-end regexes.
# ---------------------------------------------------------------------------
SAME_STRUCTURE_TAILS: list[Pattern[str]] = [
    re.compile(r"だった[。\n]"),
    re.compile(r"であった[。\n]"),
    re.compile(r"ました[。\n]"),
    re.compile(r"です[。\n]"),
    re.compile(r"ます[。\n]"),
    re.compile(r"のだ[。\n]"),
    re.compile(r"のだっ[たた]?[。\n]"),
    re.compile(r"ことだ[。\n]"),
    # Generic verb-past ending (matches「走った」「笑った」etc.)
    # Two or more identical simple-past-「った」in a row is the
    # structural-redundancy pattern LLM prose tends to produce.
    re.compile(r"[、]?った[。\n]"),
    re.compile(r"[、]?いた[。\n]"),
]

# ---------------------------------------------------------------------------
# DIRECT_EMOTION: explicit first-person internal-monologue verbs
# ---------------------------------------------------------------------------
DIRECT_EMOTION_PATTERNS: list[Pattern[str]] = [
    re.compile(r"と(思っ|感じ|考え|気づ|思わ)た[。\n]"),
    re.compile(r"と思え[るた][。\n]"),
    re.compile(r"と(思っ|感じ|考え)たのだった"),
    re.compile(r"と(思っ|感じ|考え)ずに(?:は)?いられな[いか]"),
    re.compile(r"(?:胸|心)の中"),
    re.compile(r"(?:私の?|俺の?|僕の?)心(?:は|の)中"),
]

# ---------------------------------------------------------------------------
# HEDGING_PATTERNS: epistemic hedging common in assistant prose
# ---------------------------------------------------------------------------
HEDGING_PATTERNS: list[Pattern[str]] = [
    re.compile(r"(?:かもしれ|かも|可能性|考えられ|思われ|言え)"),
    re.compile(r"(?:おそらく|たぶん|きっと)"),
    re.compile(r"(?:思います|思われます|考えられます|言えます)"),
    re.compile(r"のではないでしょうか"),
    re.compile(r"だろう[か]?"),
    re.compile(r"はず(?:だ|です|でしょう|でした)?"),
]

# ---------------------------------------------------------------------------
# TEMPLATE_PHRASES: essay/report-style connective phrases
# ---------------------------------------------------------------------------
TEMPLATE_PHRASES: list[Pattern[str]] = [
    re.compile(r"(?:重要|大切)な(?:こと|事|点)に[、とは]?"),
    re.compile(r"注目(?:すべき|したい|したいの)は"),
    re.compile(r"結論(?:として|すると|すれば)"),
    re.compile(r"まず(?:第一|最初)に"),
    re.compile(r"次に(?:、|考え(?:られる|たい))"),
    re.compile(r"最後に(?:、|まとめると|触れて)"),
    re.compile(r"総括(?:する|すると|すれば)"),
    re.compile(r"要約(?:する|すると|すれば)"),
    re.compile(r"以下(?:、|のように|の(?:通り|とおり))"),
    re.compile(r"以上(?:、|のように|の(?:通り|とおり))"),
]

# ---------------------------------------------------------------------------
# UNIFORM_PARAGRAPH: paragraph length uniformity is computed by the
# detector from split text; no patterns needed here.
# ---------------------------------------------------------------------------
UNIFORM_PARAGRAPH_MIN_PARAGRAPHS = 3  # at least 3 paragraphs to evaluate
UNIFORM_PARAGRAPH_LENGTH_TOLERANCE = 5  # characters of variance allowed

# ---------------------------------------------------------------------------
# GENERIC_VOCABULARY: abstract adjectives that LLMs love
# ---------------------------------------------------------------------------
GENERIC_VOCABULARY_TERMS: tuple[str, ...] = (
    "素晴らしい",
    "興味深い",
    "多様な",
    "重要な",
    "深刻な",
    "顕著な",
    "顕著",
    "様々な",
    "多種多様な",
    "有意義な",
    "価値ある",
    "不可欠な",
    "本質的な",
    "根本的な",
    "包括的な",
    "総合的な",
    "全体的な",
    "一般的な",
    "広範な",
    "巨大な",
    "豊富な",
)
GENERIC_VOCABULARY_PATTERN: Pattern[str] = re.compile(
    "|".join(re.escape(t) for t in GENERIC_VOCABULARY_TERMS)
)

__all__ = [
    "TRANSITION_OVERUSE_PATTERNS",
    "SAME_STRUCTURE_TAILS",
    "DIRECT_EMOTION_PATTERNS",
    "HEDGING_PATTERNS",
    "TEMPLATE_PHRASES",
    "UNIFORM_PARAGRAPH_MIN_PARAGRAPHS",
    "UNIFORM_PARAGRAPH_LENGTH_TOLERANCE",
    "GENERIC_VOCABULARY_TERMS",
    "GENERIC_VOCABULARY_PATTERN",
]
