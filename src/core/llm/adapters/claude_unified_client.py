"""Claude 統一アダプタ."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message, TextBlock

from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.backend.config import settings


class ClaudeUnifiedClient(IUnifiedLLMClient):
    """Anthropic Claude API を IUnifiedLLMClient に適合させるアダプタ."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model_name = model_name or settings.ANTHROPIC_MODEL
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        self.sync_client = anthropic.Anthropic(api_key=self.api_key)

    def _create_messages(self, req: LLMRequest) -> tuple[list[dict[str, Any]], str | None]:
        """LLMRequest からメッセージとシステムプロンプトを作成."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": req.prompt}]
        system = req.system_prompt if req.system_prompt else None
        return messages, system

    def _create_params(self, req: LLMRequest) -> dict[str, Any]:
        """LLMRequest から API パラメータを作成."""
        params: dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": req.max_tokens or 2000,
            "temperature": req.temperature,
        }
        # extra_params をマージ
        params.update(req.extra_params)
        return params

    def generate(self, req: LLMRequest) -> LLMResponse:
        """同期テキスト生成."""
        messages, system = self._create_messages(req)
        params = self._create_params(req)
        if system:
            params["system"] = system
        response: Message = self.sync_client.messages.create(**params)
        content = ""
        for block in response.content:
            if isinstance(block, TextBlock):
                content += block.text
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
        else:
            usage = LLMUsage()
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            finish_reason=response.stop_reason or "stop",
            latency_ms=0.0,  # TODO: 実際のレイテンシを測定
            parsed_json=None,
        )

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        """非同期テキスト生成."""
        messages, system = self._create_messages(req)
        params = self._create_params(req)
        if system:
            params["system"] = system
        response: Message = await self.async_client.messages.create(**params)
        content = ""
        for block in response.content:
            if isinstance(block, TextBlock):
                content += block.text
        usage = None
        if response.usage:
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
        else:
            usage = LLMUsage()
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            finish_reason=response.stop_reason or "stop",
            latency_ms=0.0,
            parsed_json=None,
        )

    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        """同期ストリーミング生成."""
        messages, system = self._create_messages(req)
        params = self._create_params(req)
        if system:
            params["system"] = system
        # 注意: Anthropic の同期ストリーミングはサポートされていない可能性がある。
        # ここでは非同期ストリーミングを同期ラッパーで実装する。
        # しかし、シンプルにするために、非同期ストリーミングを同期コンテキストで実行する。
        # 実際には、anthropic は同期ストリーミングをサポートしていないため、
        # 非同期ストリーミングを同期ラッパーでラップする。
        async def _async_stream() -> AsyncIterator[StreamChunk]:
            async with self.async_client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(text=text, is_final=False, finish_reason=None)
                # ストリーム終了時に最終チャンクを送信
                yield StreamChunk(text="", is_final=True, finish_reason=stream.stop_reason or "stop")

        # 非同期ジェネレータを同期ジェネレータに変換するために、新しいイベントループを作成
        loop = asyncio.new_event_loop()
        try:
            async_gen = _async_stream()
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        """非同期ストリーミング生成."""
        messages, system = self._create_messages(req)
        params = self._create_params(req)
        if system:
            params["system"] = system
        async with self.async_client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(text=text, is_final=False, finish_reason=None)
            # ストリーム終了時に最終チャンクを送信
            yield StreamChunk(text="", is_final=True, finish_reason=stream.stop_reason or "stop")