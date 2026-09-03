"""LLM Provider Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMProvider(ABC):
    """Interface for LLM service providers."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from prompt synchronously."""
        ...

    async def agenerate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from prompt asynchronously."""
        return self.generate(prompt, **kwargs)
