"""Japanese tokenizer with SudachiPy backend and regex fallback."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

logger = logging.getLogger(__name__)

try:
    from sudachipy import dictionary, tokenizer
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False
    dictionary = None
    tokenizer = None


STOP_WORDS = {
    "の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する",
    "ある", "いる", "こと", "もの", "これ", "それ", "あれ", "よう", "そう", "ため",
    "から", "まで", "より", "など", "そして", "しかし", "だが", "また", "その", "この",
    "あの", "どの", "という", "について", "として", "により", "による",
}


@dataclass
class TokenInfo:
    """Trimming result of a single token."""
    surface: str
    pos: str
    pos_detail: str
    reading: str
    normalized: str


@dataclass
class SudachiConfig:
    """Configuration for SudachiTokenizer."""
    split_mode: str = "C"
    include_proper: bool = True
    include_compound: bool = True
    min_length: int = 2
    dict_type: str = "core"


class JapaneseTokenizer(Protocol):
    """Protocol for Japanese tokenizer implementations."""
    def extract_nouns(
        self,
        text: str,
        include_proper: bool = True,
        include_compound: bool = True,
        min_length: int | None = None,
    ) -> List[str]:
        ...


class SudachiTokenizer:
    """SudachiPy-based Japanese tokenizer."""

    def __init__(self, config: Optional[SudachiConfig] = None) -> None:
        self.config = config or SudachiConfig()
        start = time.perf_counter()
        try:
            # dict_type: "core", "full", "small" -> maps to sudachidict_core, sudachidict_full, sudachidict_small
            dict_type = self.config.dict_type if self.config.dict_type != "core" else None
            self._tokenizer = dictionary.Dictionary(dict=dict_type).create()
            self._split_mode = getattr(tokenizer.Tokenizer.SplitMode, self.config.split_mode)
            logger.info(
                f"SudachiTokenizer initialized in {(time.perf_counter() - start) * 1000:.1f}ms "
                f"(mode={self.config.split_mode}, dict={self.config.dict_type})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize SudachiTokenizer: {e}")
            raise

    def tokenize(self, text: str) -> List[TokenInfo]:
        """Tokenize text and return detailed token info."""
        if not text:
            return []
        tokens = []
        for m in self._tokenizer.tokenize(text, self._split_mode):
            pos_parts = m.part_of_speech()
            tokens.append(TokenInfo(
                surface=m.surface(),
                pos=pos_parts[0] if pos_parts else "",
                pos_detail=pos_parts[1] if len(pos_parts) > 1 else "",
                reading=m.reading_form(),
                normalized=m.normalized_form(),
            ))
        return tokens

    def extract_nouns(
        self,
        text: str,
        include_proper: bool = True,
        include_compound: bool = True,
        min_length: int | None = None,
    ) -> List[str]:
        """Extract nouns (including proper nouns and compound nouns)."""
        if not text:
            return []

        # Use config's min_length if not explicitly provided
        effective_min_length = min_length if min_length is not None else self.config.min_length

        start = time.perf_counter()
        nouns = []
        seen = set()

        for token in self.tokenize(text):
            if token.pos != "名詞":
                continue

            if not include_proper and token.pos_detail == "固有名詞":
                continue

            if not include_compound and token.pos_detail in ("接尾", "接頭辞", "非自立", "特殊"):
                continue

            # Use surface form for katakana (normalized converts to romaji), 
            # normalized for kanji (handles okurigana, etc.)
            if re.match(r"^[ァ-ンヴー]+$", token.surface):
                base = token.surface
            else:
                base = token.normalized if token.normalized != "*" else token.surface

            if len(base) < effective_min_length:
                continue

            if base in seen:
                continue

            seen.add(base)
            nouns.append(base)

        elapsed = (time.perf_counter() - start) * 1000
        logger.debug(
            f"SudachiTokenizer.extract_nouns: {len(nouns)} nouns extracted from {len(text)} chars "
            f"in {elapsed:.1f}ms (min_length={effective_min_length})"
        )

        return nouns


class RegexJapaneseTokenizer:
    """Regex-based fallback tokenizer (original implementation)."""

    def __init__(self) -> None:
        self._pattern = re.compile(r"[一-龯]{2,}|[ァ-ンヴー]{2,}|[a-zA-Z]{3,}")

    def extract_nouns(
        self,
        text: str,
        include_proper: bool = True,
        include_compound: bool = True,
        min_length: int | None = None,
    ) -> List[str]:
        """Extract noun-like tokens using regex patterns."""
        if not text:
            return []

        effective_min_length = min_length if min_length is not None else 2
        tokens = self._pattern.findall(text)
        filtered = []
        seen = set()

        for token in tokens:
            if token in STOP_WORDS:
                continue
            if len(token) < effective_min_length:
                continue
            if token in seen:
                continue
            if token[0] in {"は", "が", "を", "に", "へ", "と", "で", "から", "より", "の", "も", "や"}:
                continue
            if token.isdigit():
                continue

            seen.add(token)
            filtered.append(token)

        return filtered


class HybridJapaneseTokenizer:
    """
    Hybrid tokenizer combining SudachiPy (precision) + Regex (compound word recall).
    
    Strategy:
    1. Extract nouns from Sudachi (proper nouns, known compounds)
    2. Extract compound tokens from Regex (long kanji/katakana sequences)
    3. Merge: prefer longer tokens, deduplicate
    """

    def __init__(self, config: Optional[SudachiConfig] = None) -> None:
        self.config = config or SudachiConfig()
        self._sudachi = SudachiTokenizer(config=self.config) if SUDACHI_AVAILABLE else None
        self._regex = RegexJapaneseTokenizer()

    def extract_nouns(
        self,
        text: str,
        include_proper: bool = True,
        include_compound: bool = True,
        min_length: int | None = None,
    ) -> List[str]:
        """Extract nouns using hybrid approach."""
        if not text:
            return []

        effective_min_length = min_length if min_length is not None else self.config.min_length

        start = time.perf_counter()

        # 1. Sudachi nouns (precision)
        sudachi_nouns = []
        if self._sudachi:
            sudachi_nouns = self._sudachi.extract_nouns(
                text,
                include_proper=include_proper,
                include_compound=include_compound,
                min_length=effective_min_length,
            )

        # 2. Regex compound tokens (recall for unknown compounds)
        regex_tokens = self._regex.extract_nouns(text, min_length=effective_min_length)

        # 3. Merge: prefer longer tokens, deduplicate
        # Strategy: sort all tokens by length descending, add if not substring of existing
        all_tokens = sudachi_nouns + regex_tokens
        all_tokens.sort(key=len, reverse=True)

        merged: list[str] = []
        for token in all_tokens:
            # Skip if this token is a substring of an already selected longer token
            is_substring = any(token in existing for existing in merged)
            if not is_substring:
                merged.append(token)

        # Sort by original order in text (approximate by first occurrence)
        merged.sort(key=lambda t: text.find(t))

        elapsed = (time.perf_counter() - start) * 1000
        logger.debug(
            f"HybridJapaneseTokenizer.extract_nouns: {len(merged)} nouns merged "
            f"(sudachi={len(sudachi_nouns)}, regex={len(regex_tokens)}) "
            f"from {len(text)} chars in {elapsed:.1f}ms (min_length={effective_min_length})"
        )

        return merged


def create_japanese_tokenizer(config: Optional[SudachiConfig] = None) -> JapaneseTokenizer:
    """Factory function to create the best available Japanese tokenizer."""
    if SUDACHI_AVAILABLE:
        try:
            return HybridJapaneseTokenizer(config=config)
        except Exception as e:
            logger.warning(f"HybridJapaneseTokenizer initialization failed, falling back to regex: {e}")

    logger.info("Using RegexJapaneseTokenizer as fallback")
    return RegexJapaneseTokenizer()


__all__ = [
    "TokenInfo",
    "SudachiConfig",
    "JapaneseTokenizer",
    "SudachiTokenizer",
    "RegexJapaneseTokenizer",
    "HybridJapaneseTokenizer",
    "create_japanese_tokenizer",
    "SUDACHI_AVAILABLE",
]