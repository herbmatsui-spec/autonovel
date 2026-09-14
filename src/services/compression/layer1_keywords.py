"""Layer 1: Keyphrase Extractor for 4-Layer Context Compression (Step 26)."""
from __future__ import annotations

import re
from collections import Counter
from typing import Tuple

from src.services.compression.models import RawTextLayerOutput
from src.services.compression.japanese_tokenizer import SudachiConfig, create_japanese_tokenizer

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None


STOP_WORDS = {
    "の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する",
    "ある", "いる", "こと", "もの", "これ", "それ", "あれ", "よう", "そう", "ため",
    "から", "まで", "より", "など", "そして", "しかし", "だが", "また", "その", "この",
    "あの", "どの", "という", "について", "として", "により", "による",
}


# Module-level tokenizer instance for tiktoken (created on first use)
_tiktoken_encoder = None


def count_tokens(text: str) -> int:
    """Approximate token count using tiktoken or character multiplier."""
    if not text:
        return 0
    try:
        import tiktoken
        global _tiktoken_encoder
        if _tiktoken_encoder is None:
            _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        return len(_tiktoken_encoder.encode(text))
    except Exception:
        return max(1, int(len(text) * 1.5))


# Module-level tokenizer instance (created on first use)
_japanese_tokenizer = None


def _get_japanese_tokenizer():
    """Get or create the Japanese tokenizer instance."""
    global _japanese_tokenizer
    if _japanese_tokenizer is None:
        _japanese_tokenizer = create_japanese_tokenizer()
    return _japanese_tokenizer


def tokenize_japanese_words(text: str) -> list[str]:
    """Tokenize Japanese text into meaningful candidate tokens (nouns, kanji words, katakana compounds)."""
    tokenizer = _get_japanese_tokenizer()
    return tokenizer.extract_nouns(text)


class Layer1KeywordExtractor:
    """Extracts top salient keyphrases from raw text using BM25 / TF-IDF / Frequency scoring."""

    def __init__(
        self,
        top_n: int = 20,
        min_score: float = 0.01,
        tokenizer_config: "SudachiConfig | None" = None,
    ) -> None:
        self.top_n = top_n
        self.min_score = min_score
        self._tokenizer_config = tokenizer_config

    def _get_tokenizer(self):
        """Get tokenizer instance, creating new one if config provided."""
        if self._tokenizer_config:
            return create_japanese_tokenizer(self._tokenizer_config)
        return _get_japanese_tokenizer()

    def extract(self, text: str, top_n: int | None = None) -> RawTextLayerOutput:
        """Extract salient keyphrases and return RawTextLayerOutput."""
        n = top_n or self.top_n
        if not text or not text.strip():
            return RawTextLayerOutput(
                extracted_keywords=[],
                keyword_scores={},
                original_char_count=0,
                original_token_count=0,
            )

        char_count = len(text)
        token_count = count_tokens(text)

        tokenizer = self._get_tokenizer()
        tokens = tokenizer.extract_nouns(
            text,
            min_length=self._tokenizer_config.min_length if self._tokenizer_config else 2,
        )
        if not tokens:
            return RawTextLayerOutput(
                extracted_keywords=[],
                keyword_scores={},
                original_char_count=char_count,
                original_token_count=token_count,
            )

        scored_keywords: list[Tuple[str, float]] = []

        # 文単位に分割して BM25 スコアリング
        sentences = [s.strip() for s in re.split(r"[。\n!?！？]+", text) if s.strip()]
        tokenized_corpus = [tokenizer.extract_nouns(s) for s in sentences if s]
        tokenized_corpus = [c for c in tokenized_corpus if c]

        freq = Counter(tokens)
        if BM25Okapi is not None and len(tokenized_corpus) >= 2:
            bm25 = BM25Okapi(tokenized_corpus)
            doc_scores: dict[str, float] = {}
            for term, count in freq.items():
                idf = bm25.idf.get(term, 1.0)
                effective_idf = max(0.1, float(idf))
                doc_scores[term] = effective_idf * count
        else:
            total = sum(freq.values()) or 1
            doc_scores = {term: count / total for term, count in freq.items()}

        # カタカナ語や長めの漢字複合語にボーナス加点（固有名詞ブースト）
        for term, sc in list(doc_scores.items()):
            boost = 1.0
            if re.match(r"^[ァ-ンヴー]{3,}$", term):
                boost = 1.4  # カタカナ固有名詞（人名・地名）
            elif len(term) >= 4 and re.match(r"^[一-龯]+$", term):
                boost = 1.2  # 複合名詞
            doc_scores[term] = sc * boost

        sorted_items = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        scored_keywords = [(term, round(score, 4)) for term, score in sorted_items if score >= self.min_score][:n]

        extracted_list = [k for k, _ in scored_keywords]
        scores_dict = {k: v for k, v in scored_keywords}

        return RawTextLayerOutput(
            extracted_keywords=extracted_list,
            keyword_scores=scores_dict,
            original_char_count=char_count,
            original_token_count=token_count,
        )


def extract_keyphrases(text: str, top_n: int = 20) -> RawTextLayerOutput:
    """Convenience function to extract keyphrases from raw text."""
    extractor = Layer1KeywordExtractor(top_n=top_n)
    return extractor.extract(text)


__all__ = ["Layer1KeywordExtractor", "extract_keyphrases", "count_tokens", "tokenize_japanese_words"]
