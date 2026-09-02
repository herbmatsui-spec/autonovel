"""モック LLM アダプタのユニットテスト。"""
from __future__ import annotations

import asyncio

from src.services.llm.mock_adapter import MockLLMAdapter


def test_mock_generate_text():
    """generate_text は決められた日本語テキストを返す。"""
    adapter = MockLLMAdapter()
    result = asyncio.run(adapter.generate_text(prompt="test prompt"))
    expected = (
        "薄暗い洞窟の奥、古びた石扉の前に立ったアルトは、静かに息を呑んだ。\n"
        "手にした魔導剣が微かに共鳴し、暗闇を青白い光が照らし出す。\n"
        "「ここが、封印の祭壇か……」\n"
        "扉に刻まれた古代文字が突如として紅く輝き、不気味な地鳴りと共に守護獣が姿を現した。"
    )
    assert result == expected


async def test_mock_generate_text_with_kwargs():
    """generate_text は余分なキーワード引数も受け入れる。"""
    adapter = MockLLMAdapter()
    result = await adapter.generate_text(
        prompt="test",
        system_prompt="sys",
        max_tokens=100,
        temperature=0.5,
        extra="value",
    )
    expected = (
        "薄暗い洞窟の奥、古びた石扉の前に立ったアルトは、静かに息を呑んだ。\n"
        "手にした魔導剣が微かに共鳴し、暗闇を青白い光が照らし出す。\n"
        "「ここが、封印の祭壇か……」\n"
        "扉に刻まれた古代文字が突如として紅く輝き、不気味な地鳴りと共に守護獣が姿を現した。"
    )
    assert result == expected


def test_mock_stream_text():
    """stream_text はチャンクをイテレートする。"""
    adapter = MockLLMAdapter()
    async def run():
        chunks = []
        async for chunk in adapter.stream_text(prompt="test prompt"):
            chunks.append(chunk)
        return chunks
    chunk_list = asyncio.run(run())
    assert len(chunk_list) == 8
    assert chunk_list[0] == "薄暗い洞窟の奥、"
