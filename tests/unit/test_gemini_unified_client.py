
import pytest
from unittest.mock import MagicMock, patch
from src.core.llm.adapters.gemini_unified_client import GeminiUnifiedClient
from src.core.llm.types import LLMRequest

@pytest.fixture
def mock_genai():
    with patch("google.genai.Client") as MockClient:
        client_instance = MagicMock()
        MockClient.return_value = client_instance
        yield client_instance

def test_gemini_unified_client_generate(mock_genai):
    client = GeminiUnifiedClient(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.text = "hello gemini"
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 5
    mock_response.usage_metadata.total_token_count = 15
    
    mock_genai.models.generate_content.return_value = mock_response
    
    req = LLMRequest(prompt="hi", system_prompt="be helpful")
    response = client.generate(req)
    
    assert response.content == "hello gemini"
    assert response.usage.total_tokens == 15
