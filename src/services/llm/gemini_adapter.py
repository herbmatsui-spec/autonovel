"""Google Gemini API アダプタ。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.retry import with_retry

logger = logging.getLogger(__name__)


class GeminiAdapter(BaseLLMAdapter):
    """Google Gemini アダプタ。"""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY or ""
        self.model_name = model_name or settings.GEMINI_MODEL
        self._model: Any = None

    def _get_model(self) -> Any:
        """モデルを遅延初期化する。"""
        if self._model is None:
            import google.generativeai as genai

            if self.api_key:
                genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
            )
        return self._model

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """テキストを一括生成する。"""
        import google.generativeai as genai

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        model = self._get_model()

        generation_config_dict: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format and response_format.get("type") in ("json_object", "json_schema"):
            generation_config_dict["response_mime_type"] = "application/json"

        async def _call() -> str:
            response = await model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(**generation_config_dict),
            )
            return response.text or ""

        return await with_retry(_call)

    async def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """テキストをストリーミング生成する。"""
        import google.generativeai as genai

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        model = self._get_model()

        response = await model.generate_content_async(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
            stream=True,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text
