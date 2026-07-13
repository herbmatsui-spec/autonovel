
import pytest

from src.services.errors import LLMTemporaryError
from src.services.retry_decorator import with_llm_retry


@pytest.mark.asyncio
async def test_with_llm_retry_success():
    class DummyClient:
        def __init__(self):
            self.calls = 0

        @with_llm_retry()
        async def generate(self, model_name="test_model", **kwargs):
            self.calls += 1
            return {"success": True}

    client = DummyClient()
    result = await client.generate(max_retries=3)
    assert result["success"] is True
    assert client.calls == 1

@pytest.mark.asyncio
async def test_with_llm_retry_retry_then_success():
    class DummyClient:
        def __init__(self):
            self.calls = 0

        @with_llm_retry()
        async def generate(self, model_name="test_model", **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise Exception("429 Too Many Requests")
            return {"success": True}

    client = DummyClient()
    result = await client.generate(max_retries=3)
    assert result["success"] is True
    assert client.calls == 3

@pytest.mark.asyncio
async def test_with_llm_retry_max_retries_exceeded():
    class DummyClient:
        def __init__(self):
            self.calls = 0

        @with_llm_retry()
        async def generate(self, model_name="test_model", **kwargs):
            self.calls += 1
            raise Exception("503 Service Unavailable")

    client = DummyClient()
    with pytest.raises(LLMTemporaryError):
        await client.generate(max_retries=2)

    assert client.calls == 5
