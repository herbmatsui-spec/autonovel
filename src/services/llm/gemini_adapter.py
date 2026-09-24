"""Google Gemini API アダプタ (google.genai 新SDK完全準拠版)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.retry import with_retry

logger = logging.getLogger(__name__)


class GeminiAdapter(BaseLLMAdapter):
    """Google Gemini アダプタ (google.genai SDK)。"""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        resolved_key = api_key
        if not resolved_key:
            resolved_key = getattr(settings, "get_gemini_api_key", lambda: settings.GEMINI_API_KEY)() or ""
        self.api_key = resolved_key
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client: Any = None

    def _get_client(self) -> Any:
        """Client を遅延初期化する。"""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key or "dummy_key_for_testing")
        return self._client

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
        client = self._get_client()
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format and response_format.get("type") in ("json_object", "json_schema"):
            config_kwargs["response_mime_type"] = "application/json"

        async def _call() -> str:
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(**config_kwargs),
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
        client = self._get_client()
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response_stream = await client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text
