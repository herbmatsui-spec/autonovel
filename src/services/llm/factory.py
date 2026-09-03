"""LLM アダプタのファクトリモジュール。"""
from __future__ import annotations

import logging

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)

# 実装済みプロバイダ（claude, ollama, vLLM 等は未実装）
IMPLEMENTED_PROVIDERS = {"gemini", "openai", "mock"}


def get_llm_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
) -> BaseLLMAdapter:
    """設定または引数に応じた LLM アダプタインスタンスを返す。

    未実装のプロバイダ (claude, ollama 等) が指定された場合は ERROR ログを出力し、
    MockLLMAdapter にフォールバックする。本番環境では空の応答になるため注意。
    """
    p = (provider or settings.LLM_PROVIDER).lower()

    if p not in IMPLEMENTED_PROVIDERS:
        logger.error(
            "LLMプロバイダ '%s' は未実装です。利用可能: %s。"
            "MockLLMAdapter にフォールバックします。本番環境では空の応答になります。",
            p,
            sorted(IMPLEMENTED_PROVIDERS),
        )
        return MockLLMAdapter()

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

    if p == "mock":
        return MockLLMAdapter()

    # フォールバック（到達しないはず）
    return MockLLMAdapter()