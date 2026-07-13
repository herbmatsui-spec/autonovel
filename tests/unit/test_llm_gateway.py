from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.llm_gateway import GeminiApiClient
from src.models import LLMRequestOptions


@pytest.mark.asyncio
async def test_gemini_api_client_generate_json():
    # Mock genai client
    mock_client = MagicMock()
    mock_cooldown = MagicMock()
    mock_cooldown.wait = AsyncMock()
    mock_cooldown.on_success = MagicMock()

    class MockResponse:
        def __init__(self, text):
            self.text = text
            self.usage_metadata = None

    mock_response = MockResponse('{"success": true}')
    mock_client.models.generate_content_async = AsyncMock(return_value=mock_response)
    mock_client.models.generate_content = MagicMock(return_value=mock_response)

    api_client = GeminiApiClient(client=mock_client, cooldown=mock_cooldown)

    request = LLMRequestOptions(
        model_name="test_model",
        prompt="Test prompt"
    )

    metadata, story, raw = await api_client.generate_json(
        model_name="test_model",
        prompt="Test prompt"
    )

    assert metadata["success"] is True
    assert story == ''
    mock_cooldown.wait.assert_called_once()
    mock_cooldown.on_success.assert_called_once()

@pytest.mark.asyncio
async def test_gemini_api_client_generate_text():
    # Mock genai client
    mock_client = MagicMock()
    mock_cooldown = MagicMock()
    mock_cooldown.wait = AsyncMock()
    mock_cooldown.on_success = MagicMock()

    class MockResponse:
        def __init__(self, text):
            self.text = text
            self.usage_metadata = None

    mock_response = MockResponse('Generated text')
    mock_client.models.generate_content_async = AsyncMock(return_value=mock_response)
    mock_client.models.generate_content = MagicMock(return_value=mock_response)

    api_client = GeminiApiClient(client=mock_client, cooldown=mock_cooldown)

    request = LLMRequestOptions(
        model_name="test_model",
        prompt="Test prompt"
    )

    text, raw = await api_client.generate_text(
        model_name="test_model",
        prompt="Test prompt"
    )

    assert text == 'Generated text'
    mock_cooldown.wait.assert_called_once()
    mock_cooldown.on_success.assert_called_once()
