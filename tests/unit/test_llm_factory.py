"""LLM ファクトリーモジュールのユニットテスト。"""
from __future__ import annotations

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


def test_get_llm_adapter_claude_with_key(monkeypatch):
    """ClaudeプロバイダーでAPIキーあり。"""
    from src.backend.config import settings
    settings.ANTHROPIC_API_KEY = "sk-ant-test-123"

    adapter = get_llm_adapter(provider="claude")
    assert adapter.__class__.__name__ == "ClaudeAdapter"


def test_get_llm_adapter_claude_without_key(monkeypatch):
    """ClaudeプロバイダーでAPIキーなしはモックフォールバック。"""
    from src.backend.config import settings
    settings.ANTHROPIC_API_KEY = ""

    adapter = get_llm_adapter(provider="claude")
    assert isinstance(adapter, MockLLMAdapter)


def test_get_llm_adapter_ollama(monkeypatch):
    """OllamaプロバイダーはAPIキー不要。"""
    from src.backend.config import settings
    settings.OLLAMA_BASE_URL = "http://localhost:11434"
    settings.OLLAMA_MODEL = "llama3.1"

    adapter = get_llm_adapter(provider="ollama")
    assert adapter.__class__.__name__ == "OllamaAdapter"


def test_get_llm_adapter_vllm(monkeypatch):
    """vLLMプロバイダーはAPIキー不要（OpenAI互換）。"""
    from src.backend.config import settings
    settings.VLLM_BASE_URL = "http://localhost:8000"
    settings.VLLM_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

    adapter = get_llm_adapter(provider="vllm")
    assert adapter.__class__.__name__ == "VLLMAdapter"
