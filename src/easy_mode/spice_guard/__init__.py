"""
SpiceGuard - 面白さの尖りを自動保護するリライト支援
"""

from __future__ import annotations

from typing import Any, Dict, List

from .extractor import SpiceExtractor
from .marker import RewritePromptBuilder, SpiceMarkerInjector
from .pattern_registry import (
    CompiledPatternCache,
    get_compiled_patterns,
    get_genre_patterns,
    get_universal_patterns,
)
from src.easy_mode.models import SpiceElement


class SpiceGuard:
    """尖り保護システム（後方互換ファサード）"""

    def __init__(self, genre: str):
        self.genre = genre
        self.extractor = SpiceExtractor(genre)
        self.marker = SpiceMarkerInjector()
        self.prompt_builder = RewritePromptBuilder(self.marker)

    def extract_spice(self, text: str) -> List[SpiceElement]:
        """テキストから尖り要素を抽出"""
        return self.extractor.extract(text)

    def inject_markers(self, text: str, elements: List[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        return self.marker.inject(text, elements)

    def remove_markers(self, text: str) -> str:
        """SPICEマーカーを除去"""
        return self.marker.remove(text)

    def build_rewrite_prompt(
        self, content: str, improvements: List[str], elements: List[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライトプロンプト構築"""
        return self.prompt_builder.build(content, improvements, elements)

    def clean_output(self, text: str) -> str:
        """出力からSPICEマーカーを除去"""
        return self.marker.clean_output(text)


# 便利関数（後方互換）
def create_spice_guard(genre: str) -> SpiceGuard:
    """SpiceGuardインスタンス生成"""
    return SpiceGuard(genre)


# 公開API
__all__ = [
    "SpiceElement",
    "SpiceGuard",
    "create_spice_guard",
    "SpiceExtractor",
    "SpiceMarkerInjector",
    "RewritePromptBuilder",
    "CompiledPatternCache",
    "get_compiled_patterns",
    "get_universal_patterns",
    "get_genre_patterns",
]
