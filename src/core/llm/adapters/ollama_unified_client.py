"""Ollama / vLLM 統一アダプタ (OpenAI 互換 API)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.backend.config import settings


class OllamaUnifiedClient(IUnifiedLLMClient):
    """Ollama / vLLM API (OpenAI 互換) を IUnifiedLLMClient に適合させるアダプタ."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or "ollama"  # Ollama では API キーは不要だが、OpenAI クライアントに渡すためダミーを設定
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.sync_client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _create_request(self, req: LLMRequest) -> dict[str, Any]:
        """LLMRequest を OpenAI API (Ollama/vLLM 互換) のリクエスト形式に変換."""
        messages = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.append({"role": "user", "content": req.prompt})

        params: dict[str, Any] = {
            "model": req.model or self.model,
            "messages": messages,
            "temperature": req.temperature,
            "stream": False,
        }
        if req.max_tokens is not None:
            params["max_tokens"] = req.max_tokens
        if req.json_mode:
            params["response_format"] = {"type": "json_object"}
        # extra_params をマージ
        params.update(req.extra_params)
        return params

    def generate(self, req: LLMRequest) -> LLMResponse:
        """同期テキスト生成."""
        params = self._create_request(req)
        response: ChatCompletion = self.sync_client.chat.completions.create(**params)
        content = response.choices[0].message.content or ""
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        else:
            usage = LLMUsage()
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            finish_reason=response.choices[0].finish_reason or "stop",
            latency_ms=0.0,  # TODO: 実際のレイテンシを測定
            parsed_json=None,
        )

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        """非同期テキスト生成."""
        params = self._create_request(req)
        response: ChatCompletion = await self.async_client.chat.completions.create(**params)
        content = response.choices[0].message.content or ""
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        else:
            usage = LLMUsage()
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            finish_reason=response.choices[0].finish_reason or "stop",
            latency_ms=0.0,
            parsed_json=None,
        )

    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        """同期ストリーミング生成."""
        params = self._create_request(req)
        params["stream"] = True
        stream = self.sync_client.chat.completions.create(**params)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta: ChoiceDelta = chunk.choices[0].delta
            text = delta.content or ""
            is_final = chunk.choices[0].finish_reason is not None
            finish_reason = chunk.choices[0].finish_reason if is_final else None
            yield StreamChunk(text=text, is_final=is_final, finish_reason=finish_reason)

    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        """非同期ストリーミング生成."""
        params = self._create_request(req)
        params["stream"] = True
        stream = await self.async_client.chat.completions.create(**params)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta: ChoiceDelta = chunk.choices[0].delta
            text = delta.content or ""
            is_final = chunk.choices[0].finish_reason is not None
            finish_reason = chunk.choices[0].finish_reason if is_final else None
            yield StreamChunk(text=text, is_final=is_final, finish_reason=finish_reason)