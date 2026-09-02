"""LLM アダプタのファクトリモジュール。"""
from __future__ import annotations

import logging

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


def get_llm_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
) -> BaseLLMAdapter:
    """設定または引数に応じた LLM アダプタインスタンスを返す。"""
    p = (provider or settings.LLM_PROVIDER).lower()

    if p == "gemini":
        resolved_key = api_key or settings.GEMINI_API_KEY
        if not resolved_key:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to MockLLMAdapter.")
            return MockLLMAdapter()
        return GeminiAdapter(api_key=resolved_key, model_name=model_name)

    if p == "openai":
        resolved_key = api_key or settings.OPENAI_API_KEY
        resolved_url = base_url or settings.OPENAI_BASE_URL
        if not resolved_key and not resolved_url:
            logger.warning("OPENAI_API_KEY/BASE_URL is not configured. Falling back to MockLLMAdapter.")
            return MockLLMAdapter()
        return OpenAIAdapter(api_key=resolved_key, base_url=resolved_url, model=model_name)

    return MockLLMAdapter()

