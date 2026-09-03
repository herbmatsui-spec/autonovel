"""Gemini LLM Provider Adapter."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.core.spi.llm.interface import ILLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMProvider(ILLMProvider):
    """Gemini LLM adapter implementation."""

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.5-flash", **kwargs: Any) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.extra_config = kwargs

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate response via Gemini API."""
        return f"[Gemini Response] {prompt[:50]}..."
