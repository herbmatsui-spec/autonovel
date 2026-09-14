import pytest
import asyncio
from src.core.llm.types import LLMRequest
from src.core.llm.adapters.mock_unified_client import UnifiedMockLLMClient

def test_mock_client():
    client = UnifiedMockLLMClient("Hello")
    req = LLMRequest(prompt="hi")
    
    # Sync
    resp = client.generate(req)
    assert resp.content == "Hello"
    assert resp.latency_ms > 0
    
    # Async
    resp_async = asyncio.run(client.agenerate(req))
    assert resp_async.content == "Hello"

    # Stream
    chunks = list(client.stream(req))
    assert len(chunks) == 1
    assert chunks[0].text == "Hello"
