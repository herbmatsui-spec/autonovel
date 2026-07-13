
import pytest
from pydantic import BaseModel

from src.services.errors import (
    LLMTemporaryError,
    LLMTokenLimitError,
    LLMUnrecoverableError,
    LLMValidationError,
)
from src.services.retry_decorator import with_llm_retry


class DummyModel(BaseModel):
    name: str

class MockLLMClient:
    def __init__(self):
        self.calls = 0

    @with_llm_retry()
    async def generate_json(self, model_name: str, prompt: str, max_retries: int = 2, retry_state=None):
        self.calls += 1
        if "token_limit" in prompt:
            raise Exception("resource exhausted: token limit exceeded")
        elif "fatal" in prompt:
            raise Exception("404 Model Not Found")
        elif "validation" in prompt:
            # Trigger Pydantic ValidationError
            DummyModel.model_validate({"name": {"nested": "dict"}})
        elif "temporary" in prompt:
            raise Exception("503 Service Unavailable")
        return {"name": "test"}, "story", None

@pytest.mark.anyio
async def test_fail_fast_token_limit():
    client = MockLLMClient()
    with pytest.raises(LLMTokenLimitError):
        await client.generate_json("gemini-1.5-flash", "token_limit", max_retries=3)
    assert client.calls == 1  # Should not retry

@pytest.mark.anyio
async def test_fail_fast_fatal():
    client = MockLLMClient()
    with pytest.raises(LLMUnrecoverableError):
        await client.generate_json("gemini-1.5-flash", "fatal", max_retries=3)
    assert client.calls == 1  # Should not retry

@pytest.mark.anyio
async def test_validation_retry_and_fail():
    client = MockLLMClient()
    with pytest.raises(LLMValidationError):
        await client.generate_json("gemini-1.5-flash", "validation", max_retries=2)
    assert client.calls == 2  # Retried once, then raised

@pytest.mark.anyio
async def test_temporary_retry_and_fail():
    client = MockLLMClient()
    with pytest.raises(LLMTemporaryError):
        await client.generate_json("gemini-1.5-flash", "temporary", max_retries=2)
    assert client.calls == 2  # Retried once, then raised
