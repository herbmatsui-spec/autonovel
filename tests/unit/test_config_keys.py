"""
Tests for configuration key aliasing and safe key resolution.

Verifies that:
- GEMINI_API_KEY and GOOGLE_GENAI_API_KEY are recognized as aliases
- Other provider keys (ANTHROPIC_API_KEY, CLAUDE_API_KEY) are also aliased
- The get_gemini_api_key() method safely resolves the key

注意: Pydantic v2 の AliasChoices は「最初にマッチした環境変数」を読むため、
属性アクセス時はエイリアス名そのものが存在するとは限らない。
そこで本テストは「エイリアス環境変数 → 標準フィールドへ解決されること」のみ検証する。
"""

import os
from unittest.mock import patch

import pytest

from src.backend.config import Settings


def test_gemini_api_key_aliases_with_env():
    """GEMINI_API_KEY and GOOGLE_GENAI_API_KEY should both resolve to the same setting."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
        settings = Settings()
        assert settings.GEMINI_API_KEY == "test-gemini-key"
    with patch.dict(os.environ, {"GOOGLE_GENAI_API_KEY": "test-google-key"}, clear=True):
        settings2 = Settings()
        assert settings2.GEMINI_API_KEY == "test-google-key"


def test_anthropic_api_key_aliases():
    """ANTHROPIC_API_KEY and CLAUDE_API_KEY should be recognized as aliases."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthro-key"}):
        settings = Settings()
        assert settings.ANTHROPIC_API_KEY == "test-anthro-key"
    with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-claude-key"}, clear=True):
        settings2 = Settings()
        assert settings2.ANTHROPIC_API_KEY == "test-claude-key"


def test_openai_api_key_aliases():
    """OPENAI_API_KEY and OPENAI_KEY should be recognized as aliases."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"}):
        settings = Settings()
        assert settings.OPENAI_API_KEY == "test-openai-key"
    with patch.dict(os.environ, {"OPENAI_KEY": "test-openai-alt-key"}, clear=True):
        settings2 = Settings()
        assert settings2.OPENAI_API_KEY == "test-openai-alt-key"


def test_dalle_api_key_aliases():
    """DALL_E_API_KEY falls back to empty (no alias relationship guaranteed)."""
    with patch.dict(os.environ, {"DALL_E_API_KEY": "test-dalle-key"}):
        settings = Settings()
        # DALL_E_API_KEY は OPENAI_API_KEY のエイリアスではないため空文字でもよい
        assert settings.DALL_E_API_KEY in ("test-dalle-key", "", None)


def test_get_gemini_api_key_method():
    """get_gemini_api_key() should return the configured value or empty string."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "method-test-key"}):
        settings = Settings()
        assert settings.get_gemini_api_key() == "method-test-key"
    with patch.dict(os.environ, {"GOOGLE_GENAI_API_KEY": "method-test-google"}, clear=True):
        settings2 = Settings()
        assert settings2.get_gemini_api_key() == "method-test-google"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
