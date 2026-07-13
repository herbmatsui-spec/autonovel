from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseFormatter(ABC):
    """テキストフォーマットの抽象基底クラス"""

    @abstractmethod
    def format(
        self,
        text: str,
        genre: str = "default",
        thinning_rate: float = 0.0,
        characters: Optional[List[Any]] = None,
        sanitizer_policy: Optional[Dict[str, Any]] = None,
        intensity: float = 0.5,
        archetypes: Optional[List[str]] = None,
        location_map: Optional[Dict[str, str]] = None,
        is_catharsis: bool = False,
        tension: int = 50,
        tension_delta: int = 0,
        **kwargs
    ) -> str:
        """
        与えられたテキストをプラットフォームや設定に合わせて整形する。
        """
        pass

