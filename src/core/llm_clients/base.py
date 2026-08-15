from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple


class BaseLLMClient(ABC):
    """LLMプロバイダクライアントの共通インターフェース。

    Gemini / OpenAI 互換など、低レベル通信クライアントはこの抽象クラスを
    継承して実装する。LLMProviderFactory は ``BaseLLMClient`` を返す。
    """

    @abstractmethod
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[Any] = None,
        nsfw_mode: bool = False,
    ) -> Tuple[Dict[str, Any], str, Any]:
        """JSON を期待する生成。戻り値は (metadata, story, usage)。"""
        raise NotImplementedError

    @abstractmethod
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[Any] = None,
        nsfw_mode: bool = False,
    ) -> Tuple[str, Any]:
        """テキスト生成。戻り値は (text, usage)。"""
        raise NotImplementedError
