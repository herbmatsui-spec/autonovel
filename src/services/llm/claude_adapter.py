"""Anthropic Claude API アダプタ。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.retry import with_retry

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseLLMAdapter):
    """Anthropic Claude アダプタ。"""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY or ""
        self.model_name = model_name or settings.ANTHROPIC_MODEL
        self._client: Any = None

    def _get_client(self) -> Any:
        """クライアントを遅延初期化する。"""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
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

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        if system_prompt:
            system = system_prompt
        else:
            system = None

        async def _call() -> str:
            response = await client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
            )
            return response.content[0].text

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

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        if system_prompt:
            system = system_prompt
        else:
            system = None

        response = await client.messages.stream(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        async with response as stream:
            async for text in stream.text_stream:
                yield text
