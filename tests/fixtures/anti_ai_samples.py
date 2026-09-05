"""Sample texts for testing the anti-AI detectors.

Each sample is labelled with which categories it should trigger so
the detector tests can assert not just "no crash" but "right answer".
"""

from __future__ import annotations

from dataclasses import dataclass

from src.services.anti_ai.models import AICategory


@dataclass
class SampleText:
    text: str
    label: str
    expected_categories: set[AICategory]


# A short, hand-written paragraph that should be CLEAN.
CLEAN_PROSE = SampleText(
    text=(
        "夜明け前の森は湿っていた。葉の一枚一枚に露が宿り、踏み出すと"
        "柔らかな音が足元から返る。遠くに小鳥の声がひとつ落ちた。"
    ),
    label="clean_prose",
    expected_categories=set(),
)


# Dense use of filler transitions — classic LLM rhythm.
TRANSITION_HEAVY = SampleText(
    text=(
        "しかし、彼は走った。さらに、止まらなかった。また、振り返った。"
        "なお、足を速めた。彼女は叫んだ。一方、雨は激しくなった。"
    ),
    label="transition_heavy",
    expected_categories={AICategory.TRANSITION_OVERUSE},
)


# Three sentences in a row with identical sentence ends.
SAME_STRUCTURE_TEXT = SampleText(
    text=(
        "彼は走った。彼女は走った。世界は走った。"
    ),
    label="same_structure",
    expected_categories={AICategory.SAME_STRUCTURE},
)


# Two explicit 「〜と思った」in a single paragraph.
DIRECT_EMOTION_TEXT = SampleText(
    text=(
        "空を見上げた。悲しいと思った。風が頬を叩く。"
        "懐かしいと感じた。ずっと、こうだと思っていた。"
        "つまらないと思った。皆、そう感じた。最後に、怒りを覚えた。"
    ),
    label="direct_emotion",
    expected_categories={AICategory.DIRECT_EMOTION},
)


# LLM hedging pile-up.
HEDGING_TEXT = SampleText(
    text=(
        "おそらく、彼はそうするかもしれません。たぶん、来ると思います。"
        "考えられますが、確証はないのではないでしょうか。"
    ),
    label="hedging",
    expected_categories={AICategory.HEDGING_PATTERNS},
)


# Essay-style template phrases.
TEMPLATE_TEXT = SampleText(
    text=(
        "重要なことに、彼は遅刻した。注目すべきは、その理由だ。"
        "結論として、謝罪は必要である。"
    ),
    label="template",
    expected_categories={AICategory.TEMPLATE_PHRASES},
)


# Three paragraphs of exactly the same length.
UNIFORM_PARAGRAPH_TEXT = SampleText(
    text=(
        "森は静かだった。霧が低く垂れていた。風が鳴っていた。"
        "\n\n" "光は弱かった。草が揺れていた。鳥が泣いていた。"
        "\n\n" "道は細かった。水が流れていた。影が伸びていた。"
    ),
    label="uniform_paragraph",
    expected_categories={AICategory.UNIFORM_PARAGRAPH},
)


# Lots of generic adjectives.
GENERIC_TEXT = SampleText(
    text=(
        "素晴らしい朝だった。興味深い人物がいた。多様な意見がある。"
        "重要な決断だ。深刻な状況だ。様々な選択肢がある。"
    ),
    label="generic_vocab",
    expected_categories={AICategory.GENERIC_VOCABULARY},
)


# Multiple categories at once — used for the integration test.
MIXED_VIOLATIONS = SampleText(
    text=(
        "しかし、さらに、また、おそらく、素晴らしい朝だ。"
        "重要なことに、結論として、彼は走るかもしれない。"
        "しかし、しかし、しかし、しかし、しかし、しかし。"
    ),
    label="mixed",
    expected_categories={
        AICategory.TRANSITION_OVERUSE,
        AICategory.HEDGING_PATTERNS,
        AICategory.GENERIC_VOCABULARY,
        AICategory.TEMPLATE_PHRASES,
    },
)


# Edge: empty.
EMPTY_TEXT = SampleText(text="", label="empty", expected_categories=set())


# Edge: too short to be meaningful.
TINY_TEXT = SampleText(text="短い。", label="tiny", expected_categories=set())


ALL_SAMPLES: tuple[SampleText, ...] = (
    CLEAN_PROSE,
    TRANSITION_HEAVY,
    SAME_STRUCTURE_TEXT,
    DIRECT_EMOTION_TEXT,
    HEDGING_TEXT,
    TEMPLATE_TEXT,
    UNIFORM_PARAGRAPH_TEXT,
    GENERIC_TEXT,
    MIXED_VIOLATIONS,
    EMPTY_TEXT,
    TINY_TEXT,
)


__all__ = [
    "SampleText",
    "CLEAN_PROSE",
    "TRANSITION_HEAVY",
    "SAME_STRUCTURE_TEXT",
    "DIRECT_EMOTION_TEXT",
    "HEDGING_TEXT",
    "TEMPLATE_TEXT",
    "UNIFORM_PARAGRAPH_TEXT",
    "GENERIC_TEXT",
    "MIXED_VIOLATIONS",
    "EMPTY_TEXT",
    "TINY_TEXT",
    "ALL_SAMPLES",
]
