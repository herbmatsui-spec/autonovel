"""LLM アダプタのファクトリモジュール。"""
from __future__ import annotations

import logging
import os

from src.backend.config import settings
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.claude_adapter import ClaudeAdapter
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.ollama_adapter import OllamaAdapter
from src.services.llm.openai_adapter import OpenAIAdapter
from src.services.llm.vllm_adapter import VLLMAdapter

logger = logging.getLogger(__name__)

IMPLEMENTED_PROVIDERS = {"gemini", "openai", "mock", "claude", "ollama", "vllm"}


def get_llm_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
) -> BaseLLMAdapter:
    """設定または引数に応じた LLM アダプタインスタンスを返す。

    未実装のプロバイダが指定された場合は WARNING ログを出力し、
    MockLLMAdapter にフォールバックする。
    """
    # In testing environment, always return mock to avoid API key requirements
    if os.environ.get("APP_ENV") == "testing":
        return MockLLMAdapter()

    p = (provider or settings.LLM_PROVIDER).lower()

    if p not in IMPLEMENTED_PROVIDERS:
        logger.warning(
            "LLMプロバイダ '%s' は未実装です。利用可能: %s。"
            "MockLLMAdapter にフォールバックします。",
            p,
            sorted(IMPLEMENTED_PROVIDERS),
        )
        return MockLLMAdapter()

    if p == "gemini":
        resolved_key = api_key or settings.GEMINI_API_KEY
        if not resolved_key:
            raise RuntimeError(
                "GEMINI_API_KEY が未設定です。.env を確認してください。"
            )
        return GeminiAdapter(api_key=resolved_key, model_name=model_name)

    if p == "openai":
        resolved_key = api_key or settings.OPENAI_API_KEY
        resolved_url = base_url or settings.OPENAI_BASE_URL
        if not resolved_key and not resolved_url:
            raise RuntimeError(
                "OPENAI_API_KEY / OPENAI_BASE_URL が未設定です。"
                ".env を確認してください。"
            )
        return OpenAIAdapter(api_key=resolved_key, base_url=resolved_url, model=model_name)

    if p == "claude":
        resolved_key = api_key or settings.ANTHROPIC_API_KEY
        if not resolved_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が未設定です。.env を確認してください。"
            )
        return ClaudeAdapter(api_key=resolved_key, model_name=model_name)

    if p == "ollama":
        resolved_url = base_url or settings.OLLAMA_BASE_URL
        return OllamaAdapter(base_url=resolved_url, model=model_name)

    if p == "vllm":
        resolved_url = base_url or settings.VLLM_BASE_URL
        return VLLMAdapter(base_url=resolved_url, model=model_name, api_key=api_key)

    if p == "mock":
        return MockLLMAdapter()

    return MockLLMAdapter()