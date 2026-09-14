
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.llm.adapters.openai_unified_client import OpenAIUnifiedClient
from src.core.llm.types import LLMRequest

@pytest.fixture
def mock_clients():
    with patch("openai.AsyncOpenAI") as MockAsync, patch("openai.OpenAI") as MockSync:
        async_instance = AsyncMock()
        sync_instance = MagicMock()
        MockAsync.return_value = async_instance
        MockSync.return_value = sync_instance
        yield async_instance, sync_instance

def test_openai_unified_client_generate(mock_clients):
    async_client, sync_client = mock_clients
    client = OpenAIUnifiedClient(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "hello"
    mock_response.model = "gpt-4o"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    sync_client.chat.completions.create.return_value = mock_response
    
    req = LLMRequest(prompt="hi", system_prompt="be helpful")
    response = client.generate(req)
    
    assert response.content == "hello"
    assert response.usage.total_tokens == 15
    
async def test_openai_unified_client_agenerate(mock_clients):
    async_client, sync_client = mock_clients
    client = OpenAIUnifiedClient(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "async hello"
    mock_response.model = "gpt-4o"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    async_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    req = LLMRequest(prompt="hi", system_prompt="be helpful")
    response = await client.agenerate(req)
    
    assert response.content == "async hello"
    assert response.usage.total_tokens == 15
