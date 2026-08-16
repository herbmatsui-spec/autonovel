"""
SpiceGuard 抽出ロジック (最適化版)
- Aho-Corasick アルゴリズム風のキーワード検索
- 文字位置インデックス事前構築による高速化
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Set

from src.easy_mode.spice_guard.pattern_registry import (
    get_compiled_patterns,
    get_genre_patterns,
    get_universal_patterns,
)
from src.easy_mode.models import SpiceElement
from src.presets.loader import load_preset


class SpiceExtractor:
    """尖り要素の抽出（最適化版）"""

    def __init__(self, genre: str):
        self.genre = genre
        self.compiled_patterns = get_compiled_patterns(genre)
        self.universal_patterns = get_universal_patterns()
        self.genre_patterns = get_genre_patterns(genre)
        self.preset = load_preset(genre)

        # キーワード検索用の逆インデックスを事前構築
        self._keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[tuple]]:
        """キーワード検索用のインデックスを構築
        戻り値: {keyword: [(pattern_type, priority, is_universal, metadata_dict), ...]}
        """
        index = defaultdict(list)

        # 普遍パターンのキーワード
        for pattern_type, config in self.universal_patterns.items():
            priority = config["priority"]
            if "keywords" in config:
                for keyword in config["keywords"]:
                    index[keyword].append((
                        pattern_type, priority, True,
                        {"keyword": keyword, "source": "universal"}
                    ))

        # ジャンル別パターンのキーワード
        for pattern_type, config in self.genre_patterns.items():
            priority = config["priority"]
            full_type = f"{self.genre}_{pattern_type}"
            if "keywords" in config:
                for keyword in config["keywords"]:
                    index[keyword].append((
                        full_type, priority, False,
                        {"keyword": keyword, "source": "genre", "pattern_type": pattern_type}
                    ))

        # キャラクター固有キーワード
        chars = self.preset.get("characters", {})
        archetypes = chars.get("archetypes", {})
        for proto_name, proto in archetypes.items():
            speech = proto.get("speech_patterns", {})
            for word in speech.get("forbidden_words", []) + speech.get("catchphrases", []):
                word_type = "forbidden" if word in speech.get("forbidden_words", []) else "catchphrase"
                index[word].append((
                    "character_voice", "high", False,
                    {"keyword": word, "source": "character",
                     "character": proto_name, "word_type": word_type}
                ))

        return dict(index)

    def extract(self, text: str) -> List[SpiceElement]:
        """テキストから尖り要素を抽出（高速化版）"""
        elements = []

        # 1. 正規表現パターンによる抽出（普遍・ジャンル別）
        elements.extend(self._extract_patterns(text))

        # 2. キーワード高速検索（Aho-Corasick風）
        elements.extend(self._extract_keywords_fast(text))

        # 3. 重複除去・ソート
        return self._deduplicate_and_sort(elements)

    def _extract_patterns(self, text: str) -> List[SpiceElement]:
        """正規表現パターンによる抽出"""
        elements = []

        # 普遍パターン
        for pattern_type, config in self.universal_patterns.items():
            priority = config["priority"]
            if "patterns" in config:
                for pattern in self.compiled_patterns.get(pattern_type, []):
                    for match in pattern.finditer(text):
                        elements.append(
                            SpiceElement(
                                type=pattern_type,
                                text=match.group(0),
                                position=match.start(),
                                priority=priority,
                                metadata={"matched_group": match.group(0), "source": "regex"},
                            )
                        )

        # ジャンル別パターン
        for pattern_type, config in self.genre_patterns.items():
            priority = config["priority"]
            full_type = f"{self.genre}_{pattern_type}"
            if "patterns" in config:
                for pattern in self.compiled_patterns.get(full_type, []):
                    for match in pattern.finditer(text):
                        elements.append(
                            SpiceElement(
                                type=full_type,
                                text=match.group(0),
                                position=match.start(),
                                priority=priority,
                                metadata={"matched_group": match.group(0), "source": "regex"},
                            )
                        )

        return elements

    def _extract_keywords_fast(self, text: str) -> List[SpiceElement]:
        """キーワード高速検索（単語境界を考慮した単純検索）
        
        より高度な Aho-Corasick 実装が必要な場合は
        `pyahocorasick` または `flashtext` ライブラリの導入を検討。
        ここでは標準ライブラリのみで実用的な高速化を行う。
        """
        elements = []
        text_lower = text.lower()

        # キーワードを長さ順でソート（長いキーワードから検索して部分マッチを防ぐ）
        sorted_keywords = sorted(self._keyword_index.keys(), key=len, reverse=True)

        for keyword in sorted_keywords:
            if keyword.lower() not in text_lower:
                continue  # 早期スキップ

            keyword_lower = keyword.lower()
            start = 0
            while True:
                pos = text_lower.find(keyword_lower, start)
                if pos == -1:
                    break

                # 単語境界チェック（日本語では緩めに）
                # 前後の文字がアルファベット/数字でない場合のみマッチとみなす
                if self._is_word_boundary(text, pos, len(keyword)):
                    for pattern_type, priority, is_universal, metadata in self._keyword_index[keyword]:
                        elements.append(
                            SpiceElement(
                                type=pattern_type,
                                text=keyword,
                                position=pos,
                                priority=priority,
                                metadata={**metadata, "source": "keyword", "matched_text": text[pos:pos+len(keyword)]},
                            )
                        )

                start = pos + 1  # 重複マッチも許可

        return elements

    def _is_word_boundary(self, text: str, pos: int, length: int) -> bool:
        """単語境界チェック（日本語混在テキスト向け緩い判定）
        
        日本語では単語境界が不明確なため、アルファベット/数字のみをチェック。
        日本語文字（ひらがな・カタカナ・漢字）は境界とみなさない。
        """
        # 前の文字チェック（アルファベット/数字のみ）
        if pos > 0:
            prev_char = text[pos - 1]
            # ASCII アルファベット/数字のみを単語構成文字とみなす
            if 'a' <= prev_char <= 'z' or 'A' <= prev_char <= 'Z' or '0' <= prev_char <= '9':
                return False

        # 次の文字チェック
        end_pos = pos + length
        if end_pos < len(text):
            next_char = text[end_pos]
            if 'a' <= next_char <= 'z' or 'A' <= next_char <= 'Z' or '0' <= next_char <= '9':
                return False

        return True

    def _deduplicate_and_sort(self, elements: List[SpiceElement]) -> List[SpiceElement]:
        """重複除去・優先度順ソート"""
        seen: Set[tuple] = set()
        unique = []

        for elem in elements:
            key = (elem.type, elem.text, elem.position)
            if key not in seen:
                seen.add(key)
                unique.append(elem)

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique.sort(key=lambda x: (priority_order.get(x.priority, 4), x.position))

        return unique