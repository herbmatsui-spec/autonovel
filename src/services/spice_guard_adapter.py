"""
SpiceGuard 統合アダプタ
EasyModePipeline の SpiceGuard を Step から呼べる形にラップ
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SpiceElement:
    """尖り要素 (EasyModePipeline.SpiceElement と互換)"""

    def __init__(
        self,
        type: str,
        text: str,
        position: int,
        priority: str = "medium",
        metadata: dict[str, Any] | None = None,
    ):
        self.type = type
        self.text = text
        self.position = position
        self.priority = priority
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"SpiceElement(type={self.type}, text={self.text[:20]}..., pos={self.position}, priority={self.priority})"


class SpiceGuardAdapter:
    """
    SpiceGuard の薄いラッパー
    - ジャンル指定で内部的に SpiceGuard を生成
    - Step から呼びやすいメソッドを提供
    """

    # 表示ジャンル名 -> 内部プリセット名マッピング
    GENRE_TO_PRESET = {
        "ファンタジー": "zarma",
        "恋愛": "aku_reijo",
        "SF": "cheat_tensei",
        "歴史": "slow_life",
        "現代": "modern_cheat",
        "官能/ロマンス": "pure_love_erotic",
        "異世界": "zarma",
        "追放ざまぁ": "zarma",
        "悪役令嬢": "aku_reijo",
        "チート転生": "cheat_tensei",
        "スローライフ": "slow_life",
        "ダンジョン運営": "dungeon_admin",
        "現代チート": "modern_cheat",
        "TS転生": "ts_tensei",
        "VRMMO": "vrmmo",
        "ループ": "loop",
    }

    def __init__(self, genre: str):
        self.genre = genre
        self.preset_name = self.GENRE_TO_PRESET.get(genre, "zarma")
        self._guard = None
        self._preset = None

    def _ensure_guard(self) -> None:
        """遅延初期化"""
        if self._guard is None:
            try:
                from src.easy_mode.spice_guard import create_spice_guard

                self._guard = create_spice_guard(self.preset_name)
                self._preset = self._guard.preset
            except Exception as e:
                logger.warning(f"SpiceGuard init failed for preset={self.preset_name}: {e}")
                # フォールバック: ダミーガード
                self._guard = _DummySpiceGuard(self.preset_name)

    def extract_spice(self, text: str) -> list[SpiceElement]:
        """テキストから尖り要素を抽出"""
        self._ensure_guard()
        try:
            raw_elements = self._guard.extract_spice(text)
            return [
                SpiceElement(
                    type=e.type,
                    text=e.text,
                    position=e.position,
                    priority=e.priority,
                    metadata=e.metadata,
                )
                for e in raw_elements
            ]
        except Exception as e:
            logger.warning(f"SpiceGuard extract_spice failed: {e}")
            return []

    def inject_markers(self, text: str, elements: list[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        self._ensure_guard()
        try:
            # 内部形式に変換
            raw_elements = self._convert_to_raw(elements)
            return self._guard.inject_markers(text, raw_elements)
        except Exception as e:
            logger.warning(f"SpiceGuard inject_markers failed: {e}")
            return text

    def clean_markers(self, text: str) -> str:
        """SPICEマーカーを除去"""
        self._ensure_guard()
        try:
            return self._guard.clean_output(text)
        except Exception as e:
            logger.warning(f"SpiceGuard clean_markers failed: {e}")
            import re

            return re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", text)

    def build_rewrite_prompt(
        self, content: str, improvements: list[str], elements: list[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライトプロンプト構築"""
        self._ensure_guard()
        try:
            raw_elements = self._convert_to_raw(elements)
            return self._guard.build_rewrite_prompt(content, improvements, raw_elements)
        except Exception as e:
            logger.warning(f"SpiceGuard build_rewrite_prompt failed: {e}")
            improvements_text = "\n".join(f"- {imp}" for imp in improvements)
            return f"""以下の小説を改善せよ。

【改善指示】
{improvements_text}

【原文】
{content}

改善後の本文のみを出力せよ。"""

    def _convert_to_raw(self, elements: list[SpiceElement]) -> list[Any]:
        """内部 SpiceElement 形式に変換"""
        from src.easy_mode.spice_guard import SpiceElement as RawSpiceElement

        return [
            RawSpiceElement(
                type=e.type,
                text=e.text,
                position=e.position,
                priority=e.priority,
                metadata=e.metadata,
            )
            for e in elements
        ]


class _DummySpiceGuard:
    """SpiceGuard 初期化失敗時のフォールバック"""

    def __init__(self, genre: str):
        self.genre = genre
        self.preset = {}

    def extract_spice(self, text: str) -> list:
        return []

    def inject_markers(self, text: str, elements: list) -> str:
        return text

    def clean_output(self, text: str) -> str:
        return text

    def build_rewrite_prompt(self, content: str, improvements: list[str], elements: list) -> str:
        improvements_text = "\n".join(f"- {imp}" for imp in improvements)
        return f"""以下の小説を改善せよ。

【改善指示】
{improvements_text}

【原文】
{content}

改善後の本文のみを出力せよ。"""


def create_spice_guard_adapter(genre: str) -> SpiceGuardAdapter:
    """ファクトリ関数"""
    return SpiceGuardAdapter(genre)
