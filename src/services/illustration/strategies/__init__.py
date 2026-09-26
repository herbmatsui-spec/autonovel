"""プロンプト戦略レジストリ。

`IllustrationType` → `PromptStrategy` の対応を一箇所で管理する。
未登録の種別は `EpisodeStrategy` へフォールバックするため、新規種別を
足してもエンジンは壊れない。
"""

from __future__ import annotations

from typing import Any, Dict, Type

from src.models.illustration import IllustrationType
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.strategies.base import (
    COMMON_NEGATIVE,
    MULTI_PANEL_NEGATIVE,
    PromptStrategy,
    detect_emotional_tone,
    distribute_paragraphs,
    split_paragraphs,
)
from src.services.illustration.strategies.character import CharacterStrategy
from src.services.illustration.strategies.cover import CoverStrategy
from src.services.illustration.strategies.episode import EpisodeStrategy
from src.services.illustration.strategies.manga24 import (
    GRID_COLS,
    GRID_ROWS,
    TOTAL_PANELS,
    Manga24Strategy,
)
from src.services.illustration.strategies.yonkoma6 import Yonkoma6Strategy

_STRATEGY_MAP: Dict[IllustrationType, Type[PromptStrategy]] = {
    IllustrationType.COVER: CoverStrategy,
    IllustrationType.CHARACTER: CharacterStrategy,
    IllustrationType.EPISODE: EpisodeStrategy,
    IllustrationType.YONKOMA: Yonkoma6Strategy,
    IllustrationType.MANGA_24PANEL: Manga24Strategy,
}

# 複数コマ（漫画シート）として扱う種別値
MULTI_PANEL_TYPE_VALUES = frozenset(
    {
        getattr(IllustrationType.YONKOMA, "value", "yonkoma"),
        getattr(IllustrationType.MANGA_24PANEL, "value", "manga_24panel"),
    }
)


def type_value(illustration_type: Any) -> str:
    """enum / str を safely な文字列へ変換する。"""
    try:
        return str(illustration_type.value)
    except AttributeError:
        return str(illustration_type)


def is_multi_panel(illustration_type: Any) -> bool:
    """複数コマ（漫画シート）種別かどうか。"""
    return type_value(illustration_type) in MULTI_PANEL_TYPE_VALUES


def get_strategy_class(illustration_type: Any) -> Type[PromptStrategy]:
    """種別に対応する戦略クラス。未登録は `EpisodeStrategy`。"""
    try:
        return _STRATEGY_MAP.get(illustration_type, EpisodeStrategy)  # type: ignore[arg-type]
    except TypeError:
        return EpisodeStrategy


def get_strategy(
    illustration_type: Any,
    config: UnifiedIllustrationConfig,
    llm: Any = None,
) -> PromptStrategy:
    """種別の戦略インスタンスを生成する。"""
    return get_strategy_class(illustration_type)(config, llm=llm)


__all__ = [
    "COMMON_NEGATIVE",
    "GRID_COLS",
    "GRID_ROWS",
    "MULTI_PANEL_NEGATIVE",
    "MULTI_PANEL_TYPE_VALUES",
    "TOTAL_PANELS",
    "CharacterStrategy",
    "CoverStrategy",
    "EpisodeStrategy",
    "Manga24Strategy",
    "PromptStrategy",
    "Yonkoma6Strategy",
    "detect_emotional_tone",
    "distribute_paragraphs",
    "get_strategy",
    "get_strategy_class",
    "is_multi_panel",
    "split_paragraphs",
    "type_value",
]
