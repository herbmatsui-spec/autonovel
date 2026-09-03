"""テストおよびローカル実行用のモック LLM アダプタ。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from src.services.llm.base import BaseLLMAdapter


class MockLLMAdapter(BaseLLMAdapter):
    """モック用 LLM アダプタ。"""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        """ストリーム中断フラグを立てる。"""
        self._cancelled = True

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        await asyncio.sleep(0.01)
        if response_format and response_format.get("type") in ("json_object", "json_schema"):
            return (
                '{"entities": [{"name": "主人公", "type": "Character", "description": "勇者", "properties": {"is_alive": true}}],'
                '"relationships": [{"source": "主人公", "target": "聖剣", "type": "POSSESSES", "detail": "所持"}],'
                '"plot_summary": "主人公が聖剣を入手した。"}'
            )

        return (
            "薄暗い洞窟の奥、古びた石扉の前に立ったアルトは、静かに息を呑んだ。\n"
            "手にした魔導剣が微かに共鳴し、暗闇を青白い光が照らし出す。\n"
            "「ここが、封印の祭壇か……」\n"
            "扉に刻まれた古代文字が突如として紅く輝き、不気味な地鳴りと共に守護獣が姿を現した。"
        )

    async def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        chunks = [
            "薄暗い洞窟の奥、",
            "古びた石扉の前に立ったアルトは、",
            "静かに息を呑んだ。\n",
            "手にした魔導剣が微かに共鳴し、",
            "暗闇を青白い光が照らし出す。\n",
            "「ここが、封印の祭壇か……」\n",
            "扉に刻まれた古代文字が突如として紅く輝き、",
            "守護獣が姿を現した。",
        ]
        delay_ms = int(kwargs.get("stream_delay_ms", 10))
        for chunk in chunks:
            if self._cancelled:
                raise asyncio.CancelledError("MockLLMAdapter cancelled")
            await asyncio.sleep(delay_ms / 1000)
            yield chunk
