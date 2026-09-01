"""テストおよびローカル実行用のモック LLM アダプタ。"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from src.services.llm.base import BaseLLMAdapter


class MockLLMAdapter(BaseLLMAdapter):
    """モック用 LLM アダプタ。"""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        await asyncio.sleep(0.05)
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
        for chunk in chunks:
            await asyncio.sleep(0.02)
            yield chunk
