"""consistency/checkers/__init__.py - チェッカーレジストリ"""
from typing import List

from src.consistency.checkers.base import Checker
from src.consistency.checkers.foreshadowing import ForeshadowingChecker
from src.consistency.checkers.timeline import TimelineChecker
from src.consistency.checkers.character import CharacterChecker
from src.consistency.checkers.world import WorldChecker
from src.consistency.checkers.duplicate import DuplicateChecker


def get_default_checkers() -> List[Checker]:
    """デフォルトで有効なチェッカー一覧を返す"""
    return [
        ForeshadowingChecker(),
        TimelineChecker(),
        CharacterChecker(),
        WorldChecker(),
        DuplicateChecker(),
    ]


__all__ = [
    "Checker",
    "CheckContext",
    "get_default_checkers",
    "ForeshadowingChecker",
    "TimelineChecker",
    "CharacterChecker",
    "WorldChecker",
    "DuplicateChecker",
]
