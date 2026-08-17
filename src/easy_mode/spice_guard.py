"""
SpiceGuard - 面白さの��（��り）を自動保護するリライト支援
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.easy_mode.spice_guard.extractor import SpiceExtractor
from src.easy_mode.spice_guard.marker import SpiceMarkerInjector, SpiceMarkerCleaner
from src.easy_mode.spice_guard.pattern_registry import get_universal_patterns, get_genre_patterns
from src.presets.loader import load_preset


@dataclass
class SpiceElement:
    """尖り要素"""

    type: str  # "unique_metaphor", "character_voice", "plot_twist_marker", "emotional_raw", "rule_break_for_effect"
    text: str  # 元のテキスト
    position: int  # 文字位置
    priority: str = "medium"  # 優先度: critical, high, medium, low


class SpiceGuard:
    """尖り保護システム（ファサード）"""

    def __init__(self, genre: str):
        self.genre = genre
        self._extractor = SpiceExtractor(genre)
        self._injector = SpiceMarkerInjector()
        self._cleaner = SpiceMarkerCleaner()

    def extract_spice(self, text: str) -> List[SpiceElement]:
        """尖り要素の自動抽出"""
        return self._extractor.extract(text)

    def inject_markers(self, text: str, elements: List[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        return self._injector.inject(text, elements)

    def remove_markers(self, text: str) -> str:
        """保護マーカーを除去"""
        return self._cleaner.remove(text)

    def build_rewrite_prompt(self, content: str, improvements: List[str], spice_elements: List[SpiceElement]) -> str:
        """SpiceGuard付きリライトプロンプト構築（テスト用公開メソッド）"""
        protected_content = self.inject_markers(content, spice_elements)
        prompt = f"""
以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』

【改善指示】
{chr(10).join(f"- {imp}" for imp in improvements)}

【原文】
{protected_content}

改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。
"""
        return prompt


def create_spice_guard(genre: str) -> SpiceGuard:
    """SpiceGuardインスタンス生成"""
    return SpiceGuard(genre)


