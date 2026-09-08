"""Japanese Morphological Tokenizer based on SudachiPy with regex fallback (Steps 13-15).

Provides robust, production-grade tokenization for novels and creative texts:
- NFKC unicode normalization
- Part-of-Speech filtering (nouns, independent verbs, adjectives)
- Novel-specific stopword exclusion
- Graceful regex fallback on SudachiPy unavailability
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Novel-specific stopwords that carry low semantic value across queries and retrieval
NOVEL_STOPWORDS: set[str] = {
    "こと", "もの", "ため", "よう", "そう", "これ", "それ", "あれ", "どれ",
    "ここ", "そこ", "あそこ", "どこ", "私", "僕", "俺", "彼", "彼女", "自分",
    "いう", "思う", "みる", "いる", "ある", "なる", "する", "いく", "くる",
    "くれる", "しまう", "おく", "わけ", "はず", "つもり", "ほう", "とき",
    "時", "前", "後", "中", "上", "下", "中", "間", "何", "誰",
    "の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ",
}


class JapaneseTokenizer:
    """Morphological tokenizer using SudachiPy with robust regex fallback."""

    def __init__(
        self,
        split_mode: str = "C",
        allowed_pos: Iterable[str] | None = None,
        excluded_sub_pos: Iterable[str] | None = None,
        stopwords: set[str] | None = None,
        use_normalized_form: bool = True,
        min_len: int = 1,
    ) -> None:
        self.split_mode_name = split_mode.upper()
        self.allowed_pos = set(allowed_pos or {"名詞", "動詞", "形容詞"})
        self.excluded_sub_pos = set(excluded_sub_pos or {"非自立", "接尾", "代名詞", "数詞"})
        self.stopwords = set(stopwords or NOVEL_STOPWORDS)
        self.use_normalized_form = use_normalized_form
        self.min_len = min_len

        self._sudachi_tokenizer = None
        self._split_mode = None
        self._init_sudachi()

    def _init_sudachi(self) -> None:
        """Initialize SudachiPy dictionary and tokenizer safely."""
        try:
            from sudachipy import dictionary, tokenizer
            self._sudachi_tokenizer = dictionary.Dictionary().create()
            if self.split_mode_name == "A":
                self._split_mode = tokenizer.Tokenizer.SplitMode.A
            elif self.split_mode_name == "B":
                self._split_mode = tokenizer.Tokenizer.SplitMode.B
            else:
                self._split_mode = tokenizer.Tokenizer.SplitMode.C
            logger.debug("SudachiPy tokenizer initialized successfully.")
        except Exception as e:
            logger.warning(f"SudachiPy initialization failed ({e}). Falling back to regex tokenizer.")
            self._sudachi_tokenizer = None

    @property
    def is_sudachi_available(self) -> bool:
        """Check whether SudachiPy is active."""
        return self._sudachi_tokenizer is not None

    def normalize_text(self, text: str) -> str:
        """Apply NFKC normalization and basic clean up."""
        if not isinstance(text, str):
            return ""
        return unicodedata.normalize("NFKC", text).strip()

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into content words (filtered by POS and stopwords)."""
        norm_text = self.normalize_text(text)
        if not norm_text:
            return []

        if self.is_sudachi_available:
            return self._sudachi_tokenize(norm_text)
        return self._regex_fallback_tokenize(norm_text)

    def _sudachi_tokenize(self, text: str) -> list[str]:
        """Tokenize using SudachiPy."""
        try:
            morphemes = self._sudachi_tokenizer.tokenize(text, self._split_mode)
            tokens: list[str] = []
            for m in morphemes:
                pos = m.part_of_speech()
                main_pos = pos[0]
                sub_pos = pos[1] if len(pos) > 1 else ""

                if main_pos not in self.allowed_pos:
                    continue
                if sub_pos in self.excluded_sub_pos:
                    continue

                word = m.normalized_form() if self.use_normalized_form else m.surface()
                word_clean = word.strip()

                if len(word_clean) < self.min_len:
                    continue
                if word_clean in self.stopwords:
                    continue

                tokens.append(word_clean)
            return tokens
        except Exception as e:
            logger.warning(f"Sudachi tokenization error: {e}. Falling back to regex.")
            return self._regex_fallback_tokenize(text)

    def _regex_fallback_tokenize(self, text: str) -> list[str]:
        """Safe fallback regex tokenizer when SudachiPy is unavailable."""
        raw_words = re.findall(r"[一-龯々〆ヵヶぁ-んァ-ンa-zA-Z0-9]+", text)
        filtered = []
        for w in raw_words:
            w_strip = w.strip()
            if len(w_strip) < self.min_len:
                continue
            if w_strip in self.stopwords:
                continue
            filtered.append(w_strip)
        return filtered
