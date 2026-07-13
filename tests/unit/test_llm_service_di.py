import pytest
from pydantic import BaseModel

from config import COOLDOWN_BASE_DEFAULT, COOLDOWN_MAX_DEFAULT, COOLDOWN_MIN_DEFAULT
from src.backend.engine_utils import AdaptiveCooldown
from src.core.container import LLMGenerateResultProxy
from src.core.llm_gateway import LLMProviderFactory
from src.models import LLMRequestOptions
from tests.mocks.mock_llm import MockGeminiApiClient


class DummySchema(BaseModel):
    key: str

@pytest.mark.asyncio
async def test_llm_service_generate_text_success():
    """
    LLMGenerateResultProxyを単体テストし、
    MockGeminiApiClientが正しく呼び出され、結果が返されることを検証する。
    """
    mock_client = MockGeminiApiClient()
    cooldown = AdaptiveCooldown(COOLDOWN_BASE_DEFAULT, COOLDOWN_MIN_DEFAULT, COOLDOWN_MAX_DEFAULT)
    factory = LLMProviderFactory(genai_client=mock_client, cooldown=cooldown)
    llm_proxy = LLMGenerateResultProxy(factory=factory)

    expected_text = "This is a mocked response."
    mock_client.add_text_response("Test prompt", expected_text)

    # 3. 実行
    request = LLMRequestOptions(
        prompt="Test prompt",
        model_name="gemini-1.5-pro",
        temp=0.7
    )
    result = await llm_proxy.generate_text(request)

    # 4. 検証
    assert result.story_content == expected_text
    assert len(mock_client.call_history) > 0
    assert mock_client.call_history[-1]["method"] == "generate_text"

@pytest.mark.asyncio
async def test_llm_service_generate_json_success():
    """
    構造化データ生成のパスを検証する。
    """
    mock_client = MockGeminiApiClient()
    cooldown = AdaptiveCooldown(COOLDOWN_BASE_DEFAULT, COOLDOWN_MIN_DEFAULT, COOLDOWN_MAX_DEFAULT)
    factory = LLMProviderFactory(genai_client=mock_client, cooldown=cooldown)
    llm_proxy = LLMGenerateResultProxy(factory=factory)

    expected_json = {"key": "value"}
    mock_client.add_json_response("Generate JSON", expected_json)

    request = LLMRequestOptions(
        prompt="Generate JSON",
        model_name="gemini-1.5-pro",
        temp=0.0,
        response_schema=DummySchema
    )

    result = await llm_proxy.generate_json(request)

    assert result.metadata["key"] == expected_json["key"]
    assert result.success is True
    assert len(mock_client.call_history) > 0
    assert mock_client.call_history[-1]["method"] == "generate_json"
