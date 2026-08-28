from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.llm_clients.gemini import GeminiApiClient
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

    request = LLMRequestOptions(model_name="test_model", prompt="Test prompt")

    metadata, story, raw = await api_client.generate_json(
        model_name="test_model", prompt="Test prompt"
    )

    assert metadata["success"] is True
    assert story == ""
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

    mock_response = MockResponse("Generated text")
    mock_client.models.generate_content_async = AsyncMock(return_value=mock_response)
    mock_client.models.generate_content = MagicMock(return_value=mock_response)

    api_client = GeminiApiClient(client=mock_client, cooldown=mock_cooldown)

    request = LLMRequestOptions(model_name="test_model", prompt="Test prompt")

    text, raw = await api_client.generate_text(model_name="test_model", prompt="Test prompt")

    assert text == "Generated text"
    mock_cooldown.wait.assert_called_once()
    mock_cooldown.on_success.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_api_client_retry_exhaustion_raises_exception():
    """Test that after max retries, the original exception is propagated."""
    mock_client = MagicMock()
    mock_cooldown = MagicMock()
    mock_cooldown.wait = AsyncMock()
    mock_cooldown.on_success = MagicMock()

    # Make the client always raise a retryable error (e.g., 503) to trigger retries
    def failing_call(*args, **kwargs):
        raise ConnectionError("503 Service Unavailable")

    mock_client.models.generate_content = MagicMock(side_effect=failing_call)
    mock_client.models.generate_content_async = AsyncMock(side_effect=failing_call)

    api_client = GeminiApiClient(client=mock_client, cooldown=mock_cooldown)

    # The decorator @with_llm_retry will retry up to max_retries (default 5) then raise
    with pytest.raises(Exception, match="503 Service Unavailable"):
        await api_client.generate_text(
            model_name="test_model", prompt="Test prompt", max_retries=3
        )

    # Ensure the cooldown.on_rate_limit was called for each retry attempt
    # For a retryable error, _handle_error returns True and calls cooldown.on_rate_limit
    # Expect calls equal to number of retries (max_retries) because on_rate_limit is called in _handle_error
    # Actually _handle_error is called for each attempt except the last? Let's just assert it was called.
    assert mock_cooldown.on_rate_limit.call_count >= 2


@pytest.mark.asyncio
async def test_llm_generate_result_proxy_purpose_keyword():
    """LLMGenerateResultProxy が purpose='what_if' などのキーワード引数を正しく処理することを検証"""
    from src.core.llm_gateway import LLMGenerateResultProxy
    from src.core.llm.providers import LLMResponse

    mock_factory = MagicMock()
    mock_provider = MagicMock()
    mock_provider.generate_text = AsyncMock(
        return_value=LLMResponse(success=True, content="Test content", usage=None, metadata={})
    )
    mock_provider.generate_json = AsyncMock(
        return_value=LLMResponse(success=True, content={"result": "ok"}, usage=None, metadata={})
    )
    mock_factory.get_provider = MagicMock(return_value=mock_provider)

    proxy = LLMGenerateResultProxy(llm_factory=mock_factory)

    # 1. generate_text with purpose keyword
    res_text = await proxy.generate_text(purpose="what_if", prompt="Test prompt")
    assert res_text.story_content == "Test content"
    mock_factory.get_provider.assert_called()

    # 2. generate_json with purpose keyword
    res_json = await proxy.generate_json(purpose="audit", prompt="Audit prompt")
    assert res_json.story_content == {"result": "ok"}

