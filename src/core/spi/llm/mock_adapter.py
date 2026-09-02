"""Mock LLM Provider Adapter."""

from __future__ import annotations

from typing import Any

from src.core.spi.llm.interface import ILLMProvider


class MockLLMProvider(ILLMProvider):
    """Mock LLM provider for tests and fallback."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a mock response."""
        return f"[Mock Response for prompt: {prompt[:30]}]"
