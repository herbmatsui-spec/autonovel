"""LLM ファクトリモジュールのユニットテスト。"""
from __future__ import annotations

import pytest

from src.backend.config import settings
from src.services.llm.factory import get_llm_adapter
from src.services.llm.mock_adapter import MockLLMAdapter


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    """各テストでLLM 関連環境変数をクリアし、独立性を担保する。"""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_BASE_URL", None)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    yield


def test_get_llm_adapter_gemini_with_key(monkeypatch):
    """GeminiプロバイダーでAPIキーあり。"""
    settings.GEMINI_API_KEY = "test-key-123"
    adapter = get_llm_adapter(provider="gemini")
    assert adapter.__class__.__name__ == "GeminiAdapter"


def test_get_llm_adapter_gemini_without_key_raises(monkeypatch):
    """GeminiプロバイダーでAPIキーなしはRuntimeError送出（フェイルFAST）。"""
    settings.GEMINI_API_KEY = None
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        get_llm_adapter(provider="gemini")


def test_get_llm_adapter_openai_with_key(monkeypatch):
    """OpenAIプロバイダーでAPIキーあり。"""
    settings.OPENAI_API_KEY = "sk-test-123"
    adapter = get_llm_adapter(provider="openai")
    assert adapter.__class__.__name__ == "OpenAIAdapter"


def test_get_llm_adapter_openai_without_key_raises(monkeypatch):
    """OpenAIプロバイダーでキー/BASE_URLなしはRuntimeError送出。"""
    settings.OPENAI_API_KEY = None
    settings.OPENAI_BASE_URL = None
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_llm_adapter(provider="openai")


def test_get_llm_adapter_openai_with_base_url_only(monkeypatch):
    """OpenAIプロバイダーで BASE_URL のみ設定されていれば通る（OpenRouter等）。"""
    settings.OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
    settings.OPENAI_API_KEY = None
    adapter = get_llm_adapter(provider="openai")
    assert adapter.__class__.__name__ == "OpenAIAdapter"


def test_get_llm_adapter_claude_with_key(monkeypatch):
    settings.ANTHROPIC_API_KEY = "sk-ant-test-123"
    adapter = get_llm_adapter(provider="claude")
    assert adapter.__class__.__name__ == "ClaudeAdapter"


def test_get_llm_adapter_claude_without_key_raises(monkeypatch):
    settings.ANTHROPIC_API_KEY = None
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_llm_adapter(provider="claude")


def test_get_llm_adapter_default_provider(monkeypatch):
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-default-123"
    adapter = get_llm_adapter()
    assert adapter.__class__.__name__ == "OpenAIAdapter"


def test_get_llm_adapter_unknown_provider_fallback():
    """未知のプロバイダーは引き続きモックへフォールバック。"""
    adapter = get_llm_adapter(provider="unknown")
    assert isinstance(adapter, MockLLMAdapter)


def test_get_llm_adapter_ollama(monkeypatch):
    settings.OLLAMA_BASE_URL = "http://localhost:11434"
    settings.OLLAMA_MODEL = "llama3.1"
    adapter = get_llm_adapter(provider="ollama")
    assert adapter.__class__.__name__ == "OllamaAdapter"


def test_get_llm_adapter_vllm(monkeypatch):
    settings.VLLM_BASE_URL = "http://localhost:8000"
    settings.VLLM_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
    adapter = get_llm_adapter(provider="vllm")
    assert adapter.__class__.__name__ == "VLLMAdapter"
