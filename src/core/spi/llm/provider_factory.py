"""LLM Provider Factory."""

from __future__ import annotations

from typing import Any, Optional

from src.core.spi.llm.gemini_adapter import GeminiLLMProvider
from src.core.spi.llm.interface import ILLMProvider
from src.core.spi.llm.mock_adapter import MockLLMProvider


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    def __init__(self, **kwargs: Any) -> None:
        self.default_kwargs = kwargs

    def create(self, provider_type: str = "mock", **kwargs: Any) -> ILLMProvider:
        """Create an LLM provider instance."""
        merged_kwargs = {**self.default_kwargs, **kwargs}
        if provider_type.lower() == "gemini":
            return GeminiLLMProvider(**merged_kwargs)
        return MockLLMProvider(**merged_kwargs)
