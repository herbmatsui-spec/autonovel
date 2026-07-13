from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """LLMからの共通レスポンス形式"""
    content: str
    metadata: Dict[str, Any] = {}
    usage: Dict[str, int] = {}
    success: bool = True
    error: Optional[str] = None

class LLMProvider(ABC):
    """
    LLMプロバイダーの共通インターフェース。
    特定のSDK（Gemini, OpenAI等）に依存せず、アプリケーション層からLLMを操作可能にする。
    """

    @abstractmethod
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        pass

    @abstractmethod
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """構造化データ(JSON)生成"""
        pass
