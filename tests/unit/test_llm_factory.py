"""LLM ファクトリーモジュールのユニットテスト。"""
from __future__ import annotations

import pytest

from src.services.llm.factory import get_llm_adapter
from src.services.llm.mock_adapter import MockLLMAdapter


def test_get_llm_adapter_gemini_with_key(monkeypatch):
    """GeminiプロバイダーでAPIキーあり。"""
    from src.backend.config import settings
    settings.GEMINI_API_KEY = "test-key-123"

    adapter = get_llm_adapter(provider="gemini")
    assert adapter.__class__.__name__ == "GeminiAdapter"


def test_get_llm_adapter_gemini_without_key(monkeypatch):
    """GeminiプロバイダーでAPIキーなしはモックフォールバック。"""
    from src.backend.config import settings
    settings.GEMINI_API_KEY = ""

    adapter = get_llm_adapter(provider="gemini")
    assert isinstance(adapter, MockLLMAdapter)


def test_get_llm_adapter_openai_with_key(monkeypatch):
    """OpenAIプロバイダーでAPIキーあり。"""
    from src.backend.config import settings
    settings.OPENAI_API_KEY = "sk-test-123"

    adapter = get_llm_adapter(provider="openai")
    assert adapter.__class__.__name__ == "OpenAIAdapter"


def test_get_llm_adapter_openai_without_key(monkeypatch):
    """OpenAIプロバイダーでAPIキーなしはモックフォールバック。"""
    from src.backend.config import settings
    settings.OPENAI_API_KEY = ""

    adapter = get_llm_adapter(provider="openai")
    assert isinstance(adapter, MockLLMAdapter)


def test_get_llm_adapter_default_provider(monkeypatch):
    """デフォルトプロバイダー（設定値）を使用する。"""
    from src.backend.config import settings
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-default-123"

    adapter = get_llm_adapter()
    assert adapter.__class__.__name__ == "OpenAIAdapter"


def test_get_llm_adapter_unknown_provider_fallback():
    """未知のプロバイダーはモックにフォールバックする。"""
    adapter = get_llm_adapter(provider="unknown")
    assert isinstance(adapter, MockLLMAdapter)