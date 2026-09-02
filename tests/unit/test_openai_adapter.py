"""OpenAI アダプタのユニットテスト。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm.openai_adapter import OpenAIAdapter


@pytest.fixture
def mock_client():
    """AsyncOpenAI クライアントのモック。"""
    with patch("src.services.llm.openai_adapter.AsyncOpenAI") as cls:
        instance = AsyncMock()
        cls.return_value = instance
        # chat.completions.create のモック
        mock_choice = AsyncMock()
        mock_choice.message.content = "Generated story text..."
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        instance.chat.completions.create.return_value = mock_response
        yield instance


def test_openai_adapter_init_with_key():
    """OpenAIAdapter は API キーで初期化できる。"""
    adapter = OpenAIAdapter(api_key="sk-test-123", model="gpt-4")
    assert adapter.api_key == "sk-test-123"
    assert adapter.model == "gpt-4"


def test_openai_adapter_init_default_key():
    """OpenAIAdapter はデフォルトキーで初期化される。"""
    from src.backend.config import settings
    settings.OPENAI_API_KEY = "sk-default-456"

    adapter = OpenAIAdapter()
    assert adapter.api_key == "sk-default-456"


async def test_openai_generate_text(mock_client):
    """generate_text はプロンプトからテキストを生成する。"""
    adapter = OpenAIAdapter()
    result = await adapter.generate_text(prompt="Once upon a time...")
    assert result == "Generated story text..."


async def test_openai_generate_text_with_system_prompt(mock_client):
    """generate_text は system プロンプトもサポートする。"""
    adapter = OpenAIAdapter()
    result = await adapter.generate_text(
        prompt="Write a story",
        system_prompt="You are a creative writer.",
    )
    assert result == "Generated story text..."


async def test_openai_stream_text(mock_client):
    """stream_text はストリームからチャンクをyieldする。"""
    adapter = OpenAIAdapter()

    # チャンクオブジェクトのモック
    mock_delta = MagicMock()
    mock_delta.content = "Generated story text..."
    mock_choice = MagicMock()
    mock_choice.delta = mock_delta
    mock_chunk = MagicMock()
    mock_chunk.choices = [mock_choice]

    async def mock_stream():
        yield mock_chunk

    adapter.client.chat.completions.create.return_value = mock_stream()

    chunks = []
    async for chunk in adapter.stream_text(prompt="Hello"):
        chunks.append(chunk)
    assert chunks == ["Generated story text..."]
