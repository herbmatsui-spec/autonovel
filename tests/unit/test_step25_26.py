"""
Unit tests verifying Step 25 & Step 26:
- Step 25: Orchestrator shared instance state retention across system router calls.
- Step 26: OpenAIProvider isinstance and fallback exception mapping.
"""
import pytest
from src.core.exceptions import (
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMTimeoutError,
    LLMServerError,
    LLMContentFilterError,
    LLMUnknownError,
)
from src.backend.engine_utils import AdaptiveCooldown
from src.llm.openai_provider import OpenAIProvider


def test_step25_shared_orchestrator_singleton():
    """Verify get_shared_orchestrator returns the same instance and keeps state."""
    from src.backend.routers.system import get_shared_orchestrator

    orch1 = get_shared_orchestrator()
    orch2 = get_shared_orchestrator()
    assert orch1 is orch2

    # Verify setting version mutates the shared instance
    orch1.set_skill_version("v2")
    assert orch2.get_active_version() == "v2"

    # Restore v1
    orch1.set_skill_version("v1")
    assert orch2.get_active_version() == "v1"


def test_step26_openai_provider_exception_mapping():
    """Verify _map_exception maps various exceptions accurately."""
    provider = OpenAIProvider(cooldown=AdaptiveCooldown(1.0, 0.5, 5.0))

    # String fallback checks
    mapped = provider._map_exception(RuntimeError("429 Too Many Requests"))
    assert isinstance(mapped, LLMRateLimitError)

    mapped = provider._map_exception(RuntimeError("401 Unauthorized auth error"))
    assert isinstance(mapped, LLMAuthenticationError)

    mapped = provider._map_exception(RuntimeError("400 Invalid argument"))
    assert isinstance(mapped, LLMInvalidRequestError)

    mapped = provider._map_exception(RuntimeError("Content filter blocked prompt"))
    assert isinstance(mapped, LLMContentFilterError)

    mapped = provider._map_exception(RuntimeError("500 Internal Server error"))
    assert isinstance(mapped, LLMServerError)

    mapped = provider._map_exception(TimeoutError("Request timeout"))
    assert isinstance(mapped, LLMTimeoutError)

    mapped = provider._map_exception(Exception("Some weird thing"))
    assert isinstance(mapped, LLMUnknownError)
