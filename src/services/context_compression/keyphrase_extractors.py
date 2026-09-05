# src/services/context_compression/keyphrase_extractors.py
"""キーフレーズ抽出器実装群 (第1層)"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


class KeyphraseExtractor(ABC):
    """キーフレーズ抽出器の基底クラス"""
     
    @abstractmethod
    def extract(self, text: str, top_k: int, min_score: float) -> List[Tuple[str, float]]:
        """テキストからキーフレーズを抽出
        
        Args:
            text: 対象テキスト
            top_k: 抽出する最大件数
            min_score: 最小スコア閾値
            
        Returns:
            (キーフレーズ, スコア) のタプルリスト
        """
        pass


class TFIDFExtractor(KeyphraseExtractor):
    """日本語名詞抽出ベースのキーフレーズ抽出器（TF-IDF風スコアリング）"""
     
    def __init__(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._sklearn_available = True
        except ImportError:
            logger.warning("scikit-learn not available, TFIDFExtractor will use fallback")
            self._sklearn_available = False
     
    def extract(self, text: str, top_k: int, min_score: float) -> List[Tuple[str, float]]:
        """日本語名詞を抽出し、TF-IDF風スコアで返す"""
        try:
            # 日本語名詞を抽出
            nouns = self._extract_japanese_nouns(text)
            
            if not nouns:
                return []
            
            # TF-IDF風スコア計算
            sentences = re.split(r'[。．！？!?\n]', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
            
            if len(sentences) >= 2 and self._sklearn_available:
                return self._compute_tfidf_scores(nouns, sentences, top_k, min_score)
            else:
                return self._compute_frequency_scores(nouns, text, top_k, min_score)
        except Exception as e:
            logger.error(f"TFIDFExtractor failed: {e}")
            return []
     
    def _extract_japanese_nouns(self, text: str) -> List[str]:
        """日本語名詞らしきパターンを抽出（正規表現ベース）"""
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
            r'(?<=[はがをにへとでからまでよりのもやなどて])[\u4e00-\u9fff]{2,}(?=[。．!?\n\s])',
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
     
    def _compute_tfidf_scores(self, nouns: List[str], sentences: List[str], top_k: int, min_score: float) -> List[Tuple[str, float]]:
        """TF-IDFスコア計算"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            vectorizer = TfidfVectorizer(
                vocabulary=nouns,
                lowercase=False,
                token_pattern=r'(?u)\b\w+\b'
            )
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()
            mean_scores = tfidf_matrix.mean(axis=0).A1
            
            scored = list(zip(feature_names, mean_scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            
            result = [(term, float(score)) for term, score in scored if score >= min_score]
            return result[:top_k]
        except Exception:
            return self._compute_frequency_scores(nouns, "", top_k, min_score)
     
    def _compute_frequency_scores(self, nouns: List[str], text: str, top_k: int, min_score: float) -> List[Tuple[str, float]]:
        """頻度ベーススコア計算"""
        counts = Counter()
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
        """機能語判定"""
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


class KeyBERTExtractor(KeyphraseExtractor):
    """KeyBERTベースのキーフレーズ抽出器"""
     
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from keybert import KeyBERT
            self.kw_model = KeyBERT(model=model_name)
            self._available = True
        except ImportError:
            logger.warning("keybert not available, KeyBERTExtractor will not work")
            self._available = False
        except Exception as e:
            logger.warning(f"KeyBERT model load failed: {e}")
            self._available = False
     
    def extract(self, text: str, top_k: int, min_score: float) -> List[Tuple[str, float]]:
        if not self._available:
            return []
         
        try:
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words=None,
                use_mmr=True,
                diversity=0.5,
                top_n=top_k * 2
            )
             
            result = [(kw, float(score)) for kw, score in keywords 
                      if score >= min_score][:top_k]
             
            return result
        except Exception as e:
            logger.error(f"KeyBERTExtractor failed: {e}")
            return []


class BM25Extractor(KeyphraseExtractor):
    """BM25ベースのキーフレーズ抽出器"""
     
    def __init__(self):
        try:
            from rank_bm25 import BM25Okapi
            self._available = True
        except ImportError:
            logger.warning("rank_bm25 not available, BM25Extractor will not work")
            self._available = False
     
    def _tokenize(self, text: str) -> List[str]:
        """簡易トークナイズ（日本語対応の簡易版）"""
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
     
    def extract(self, text: str, top_k: int, min_score: float) -> List[Tuple[str, float]]:
        if not self._available:
            return []
         
        try:
            from rank_bm25 import BM25Okapi
            
            sentences = re.split(r'[。．！？!?\n]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) < 2:
                tokens = self._tokenize(text)
                return [(token, 1.0) for token in tokens[:top_k]]
            
            tokenized_corpus = [self._tokenize(s) for s in sentences]
            
            from rank_bm25 import BM25Okapi
            bm25 = BM25Okapi(tokenized_corpus)
            
            query_tokens = self._tokenize(text)
            scores = bm25.get_scores(query_tokens)
            
            scored_sentences = list(zip(sentences, scores))
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            
            result = [(sent, float(score)) for sent, score in scored_sentences 
                      if score >= min_score][:top_k]
            
            return result
        except Exception as e:
            logger.error(f"BM25Extractor failed: {e}")
            return []


def create_extractor(method: str) -> 'KeyphraseExtractor':
    """抽出器ファクトリ関数"""
    extractors = {
        "tfidf": TFIDFExtractor,
        "keybert": KeyBERTExtractor,
        "bm25": BM25Extractor,
    }
    
    if method not in extractors:
        raise ValueError(f"Unknown extractor method: {method}. Available: {list(extractors.keys())}")
    
    return extractors[method]()


__all__ = ['KeyphraseExtractor', 'TFIDFExtractor', 'KeyBERTExtractor', 'BM25Extractor', 'create_extractor']