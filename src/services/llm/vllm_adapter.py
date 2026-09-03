"""vLLM API アダプタ (OpenAI 互換 API)。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.retry import with_retry

logger = logging.getLogger(__name__)


class VLLMAdapter(BaseLLMAdapter):
    """vLLM API アダプタ (OpenAI 互換モード)。"""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url or settings.VLLM_BASE_URL
        self.model = model or settings.VLLM_MODEL
        self.api_key = api_key or "vllm"
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

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
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        call_kwargs = dict(kwargs)
        if response_format is not None:
            call_kwargs["response_format"] = response_format

        async def _call() -> str:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **call_kwargs,
            )
            choice = response.choices[0]
            return choice.message.content or ""

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
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
