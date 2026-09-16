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


# 旧API互換抽出器クラス群
class KeyphraseExtractor:
    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        raise NotImplementedError


class TFIDFExtractor(KeyphraseExtractor):
    def __init__(self):
        self.extractor = Layer1KeywordExtractor()

    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        res = self.extractor.extract(text, top_n=top_k)
        return [(k, v) for k, v in res.keyword_scores.items() if v >= min_score][:top_k]

    # 旧API互換プライベートメソッド
    def _extract_japanese_nouns(self, text: str) -> list[str]:
        """日本語名詞らしきパターンを抽出（正規表現ベース） - 旧実装と互換性を保つため"""
        patterns = [
            # 漢字2文字以上の熟語（名詞っぽい）
            r'[\u4e00-\u9fff]{2,}',
            # カタカナ語（外来語・固有名詞）
            r'[\u30a0-\u30ff]{2,}',
            # ひらがな＋漢字の混在（3文字以上）
            r'[\u3040-\u309f]{1,}[\u4e00-\u9fff]+',
            # 漢字＋ひらがなの混在（例: 旅立）
            r'[\u4e00-\u9fff]+[\u3040-\u309f]+',
            # 漢字＋カタカナの混在
            r'[\u4e00-\u9fff]+[\u30a0-\u30ff]+',
            # 英数字
            r'[a-zA-Z0-9]{2,}',
            # 単体の漢字（助詞の前後などで単独で現れるもの）
            r'(?<=[はがをにへとでからまでよりのもやなどにて])[\u4e00-\u9fff](?=[。．！？!?\n\s])',
            r'(?<=[はがをにへとでからまでよりのもやなどて])[\u4e00-\u9fff]{2,}(?=[。．！？!?\n\s])',
            r'[\u4e00-\u9fff](?=[はがをにへとでからまでよりのもやなどて])',
            r'[\u4e00-\u9fff]{2,}(?=[はがをにへとでからまでよりのもやなどて])',
        ]

        nouns = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            nouns.extend(matches)

        # 重複除去・フィルタリング
        filtered = []
        seen = set()
        for noun in nouns:
            if noun in seen:
                continue
            if len(noun) < 2 and not (len(noun) == 1 and '\u4e00' <= noun <= '\u9fff'):
                continue
            if self._is_function_word(noun):
                continue
            if noun.isdigit():
                continue
            # 削除: 助詞で始まる名詞（例: の剣士）
            if noun[0] in {'は', 'が', 'を', 'に', 'へ', 'と', 'で', 'から', 'より', 'の', 'も', 'や'}:
                continue
            seen.add(noun)
            filtered.append(noun)

        return filtered

    def _compute_tfidf_scores(self, nouns: list[str], sentences: list[str], top_k: int, min_score: float) -> list[tuple[str, float]]:
        """Compute TF-IDF scores - simplified implementation for compatibility"""
        # Create a temporary text from sentences for scoring
        text = "。".join(sentences) if sentences else ""
        res = self.extractor.extract(text, top_n=len(nouns))
        scored_items = [(k, v) for k, v in res.keyword_scores.items() if v >= min_score]
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return scored_items[:top_k]

    def _compute_frequency_scores(self, nouns: list[str], text: str, top_k: int, min_score: float) -> list[tuple[str, float]]:
        """Compute frequency-based scores"""
        if not nouns:
            return []
        counts = {}
        for noun in nouns:
            count = text.count(noun)
            if count > 0:
                counts[noun] = count

        if not counts:
            return []

        total = sum(counts.values())
        scored = [(noun, count / total) for noun, count in counts.items() if count / total >= min_score]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _is_function_word(self, word: str) -> bool:
        """Check if word is a function word"""
        function_words = {
            'は', 'が', 'を', 'に', 'へ', 'と', 'で', 'から', 'まで', 'より', 'の', 'も', 'や', 'など',
            'にて', 'として', 'について', 'において', 'よって', 'のため', 'ように', 'ために',
            'だ', 'です', 'である', 'だっ', 'だった', 'ます', 'ませ', 'まし', 'ましょう',
            'ない', 'ぬ', 'ん', 'れる', 'られる', 'せる', 'させる', 'たい', 'たがる',
            'そして', 'しかし', 'したがって', 'また', 'さらに', 'つまり', 'すなわち', 'ただし',
            'これ', 'それ', 'あれ', 'この', 'その', 'あの', 'ここ', 'そこ', 'あそこ',
            '私', 'わたし', '僕', 'ぼく', '俺', 'あなた', '貴方', '彼', '彼女',
        }
        return word in function_words or word.isdigit()


class BM25Extractor(KeyphraseExtractor):
    def __init__(self):
        self.extractor = Layer1KeywordExtractor()

    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        res = self.extractor.extract(text, top_n=top_k)
        return [(k, v) for k, v in res.keyword_scores.items() if v >= min_score][:top_k]

    # 旧API互換プライベートメソッド
    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization (Japanese compatible)"""
        import unicodedata
        result = []
        current = ""
        for ch in text:
            cat = unicodedata.category(ch)
            if cat.startswith('L') or cat.startswith('N'):
                current += ch
            else:
                if current:
                    result.append(current)
                    current = ""
        if current:
            result.append(current)
        final = []
        for token in result:
            if len(token) <= 3:
                final.append(token)
            else:
                for i in range(len(token) - 1):
                    final.append(token[i:i+2])
        return final if final else [text]


class KeyBERTExtractor(KeyphraseExtractor):
    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        try:
            from keybert import KeyBERT
            kw = KeyBERT()
            return kw.extract_keywords(text, top_n=top_k)
        except Exception:
            return []


def create_extractor(method: str) -> KeyphraseExtractor:
    mapping = {
        "tfidf": TFIDFExtractor,
        "bm25": BM25Extractor,
        "keybert": KeyBERTExtractor,
    }
    if method not in mapping:
        raise ValueError(f"Unknown extractor method: {method}. Available: {list(mapping.keys())}")
    return mapping[method]()


__all__ = [
    "Layer1KeywordExtractor",
    "extract_keyphrases",
    "count_tokens",
    "tokenize_japanese_words",
    "KeyphraseExtractor",
    "TFIDFExtractor",
    "BM25Extractor",
    "KeyBERTExtractor",
    "create_extractor",
]
