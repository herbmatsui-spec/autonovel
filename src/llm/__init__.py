"""Deprecated LLM module.

This module is deprecated. Use `src.core.llm.providers` instead.
"""
import warnings

warnings.warn(
    "src.llm is deprecated. Use src.core.llm.providers instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from src.core.llm.providers import (
    LLMProvider,
    LLMResponse,
    GeminiProvider,
    OpenAIProvider,
    LLMProviderFactory,
)

from src.core.llm.router import (
    is_openai_compatible,
    select_model,
    resolve_model,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "GeminiProvider",
    "OpenAIProvider",
    "LLMProviderFactory",
    "is_openai_compatible",
    "select_model",
    "resolve_model",
]