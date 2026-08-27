"""tests/unit/test_llm_service_nsfw.py
LLMService における nsfw_mode 伝搬の単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.llm_service import LLMService
from src.core.llm.providers.base import LLMResponse


@pytest.mark.asyncio
async def test_llm_service_generate_text_propagates_nsfw_mode():
    service = LLMService(api_key="fake-key")

    mock_provider = AsyncMock()
    mock_provider.generate_text.return_value = LLMResponse(content="Erotic scene text", success=True)

    mock_factory = MagicMock()
    mock_factory.get_provider.return_value = mock_provider
    service._factory = mock_factory

    result = await service.generate_text(
        purpose="writing",
        prompt="Write a passionate scene.",
        nsfw_mode=True,
        temperature=0.8,
    )

    assert result == "Erotic scene text"
    mock_provider.generate_text.assert_awaited_once()
    _, kwargs = mock_provider.generate_text.call_args
    assert kwargs.get("nsfw_mode") is True
    assert kwargs.get("temperature") == 0.8


@pytest.mark.asyncio
async def test_llm_service_generate_json_propagates_nsfw_mode():
    service = LLMService(api_key="fake-key")

    mock_provider = AsyncMock()
    mock_provider.generate_json.return_value = LLMResponse(
        content="{}", metadata={"scene": "intimate"}, success=True
    )

    mock_factory = MagicMock()
    mock_factory.get_provider.return_value = mock_provider
    service._factory = mock_factory

    result = await service.generate_json(
        purpose="writing",
        prompt="Generate JSON with erotic parameters.",
        nsfw_mode=True,
    )

    assert result["success"] is True
    assert result["metadata"] == {"scene": "intimate"}
    mock_provider.generate_json.assert_awaited_once()
    _, kwargs = mock_provider.generate_json.call_args
    assert kwargs.get("nsfw_mode") is True
