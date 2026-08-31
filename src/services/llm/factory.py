"""LLM アダプタのファクトリモジュール。"""
from __future__ import annotations

import logging

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


def get_llm_adapter(provider: str | None = None) -> BaseLLMAdapter:
    """設定または引数に応じた LLM アダプタインスタンスを返す。"""
    p = (provider or settings.LLM_PROVIDER).lower()

    if p == "gemini":
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to MockLLMAdapter.")
            return MockLLMAdapter()
        return GeminiAdapter()

    if p == "openai":
        if not settings.OPENAI_API_KEY and not settings.OPENAI_BASE_URL:
            logger.warning("OPENAI_API_KEY/BASE_URL is not configured. Falling back to MockLLMAdapter.")
            return MockLLMAdapter()
        return OpenAIAdapter()

    return MockLLMAdapter()
