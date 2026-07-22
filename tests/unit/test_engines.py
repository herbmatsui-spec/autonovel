
import pytest
from pydantic import BaseModel, ValidationError

from src.services.retry_decorator import RetryState, with_llm_retry


class DummyModel(BaseModel):
    name: str

class MockCooldown:
    def __init__(self):
        self.waits = 0
        self.successes = 0
        self.errors = 0
        self.rate_limits = 0

    async def wait(self):
        self.waits += 1

    def on_success(self):
        self.successes += 1

    def on_error(self):
        self.errors += 1

    def on_rate_limit(self):
        self.rate_limits += 1


class MockLLMClient:
    def __init__(self):
        self.cooldown = MockCooldown()
        self._lock = None
        self._active_requests = 0
        self._consecutive_5xx = 0
        self.calls = 0
        self.fail_until = 0
        self.fail_with_validation = False
        self.fail_with_503 = False

    @with_llm_retry()
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        temp: float = 0.7,
        max_retries: int = 3,
        retry_state: RetryState = None
    ):
        self.calls += 1
        if self.calls <= self.fail_until:
            if self.fail_with_validation:
                # Raise ValidationError
                # In Pydantic V2, validation errors require a model
                try:
                    DummyModel(name=123)  # This will succeed since Pydantic coerses int to str, let's pass a dict
                    DummyModel.model_validate({"name": {"nested": "dict"}})
                except ValidationError as ve:
                    raise ve
            elif self.fail_with_503:
                raise Exception("503 Service Unavailable")
            else:
                raise Exception("Connection Timeout")
        return {"name": "test"}, "story", None


@pytest.mark.anyio
async def test_retry_decorator_success_first_try():
    client = MockLLMClient()
    res = await client.generate_json("gemini-1.5-flash", "hello")
    assert res == ({"name": "test"}, "story", None)
    assert client.calls == 1
    assert client.cooldown.successes == 1
    assert client._active_requests == 0


@pytest.mark.anyio
async def test_retry_decorator_retry_on_validation_error():
    client = MockLLMClient()
    client.fail_until = 1
    client.fail_with_validation = True

    res = await client.generate_json("gemini-1.5-flash", "hello")
    assert res == ({"name": "test"}, "story", None)
    assert client.calls == 2
    assert client.cooldown.successes == 1
    assert client._active_requests == 0


@pytest.mark.anyio
async def test_retry_decorator_retry_on_503():
    client = MockLLMClient()
    client.fail_until = 1
    client.fail_with_503 = True

    res = await client.generate_json("gemini-1.5-flash", "hello")
    assert res == ({"name": "test"}, "story", None)
    assert client.calls == 2
    assert client.cooldown.successes == 1
    assert client.cooldown.rate_limits == 1
    assert client._active_requests == 0
