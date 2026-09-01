"""LLM アダプタの抽象基底クラス。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class BaseLLMAdapter(ABC):
    """LLM プロバイダの共通インターフェース。"""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """テキストを一括生成する。"""
        raise NotImplementedError

    @abstractmethod
    async def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """テキストをストリーミング生成する。"""
        raise NotImplementedError
        yield ""  # generator 型ヒント用
