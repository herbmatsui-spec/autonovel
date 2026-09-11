"""
Tests for configuration key aliasing and safe key resolution.

Verifies that:
- GEMINI_API_KEY and GOOGLE_GENAI_API_KEY are recognized as aliases
- Other provider keys (ANTHROPIC_API_KEY, CLAUDE_API_KEY) are also aliased
- The get_gemini_api_key() method safely resolves the key
"""

import os
import pytest
from unittest.mock import patch

# We'll import the Settings class directly to test with environment overrides
from src.backend.config import Settings


def test_gemini_api_key_aliases_with_env():
    """GEMINI_API_KEY and GOOGLE_GENAI_API_KEY should both resolve to the same setting."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
        settings = Settings()
        assert settings.GEMINI_API_KEY == "test-gemini-key"
        # The AliasChoices means GOOGLE_GENAI_API_KEY should also read the same env var
        # but note: AliasChoices in Pydantic v2 reads the first matching env var.
        # Setting GEMINI_API_KEY should make settings.GOOGLE_GENAI_API_KEY also "test-gemini-key"
        # because validation_alias reads from the list; but when we access the attribute,
        # it returns the resolved value.
        # Let's verify:
        assert settings.GOOGLE_GENAI_API_KEY == "test-gemini-key"
        # Also test that setting GOOGLE_GENAI_API_KEY alone works
    with patch.dict(os.environ, {"GOOGLE_GENAI_API_KEY": "test-google-key"}, clear=True):
        settings2 = Settings()
        assert settings2.GEMINI_API_KEY == "test-google-key"
        assert settings2.GOOGLE_GENAI_API_KEY == "test-google-key"


def test_anthropic_api_key_aliases():
    """ANTHROPIC_API_KEY and CLAUDE_API_KEY should be recognized as aliases."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthro-key"}):
        settings = Settings()
        assert settings.ANTHROPIC_API_KEY == "test-anthro-key"
        # The alias is defined as AliasChoices("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
        assert settings.CLAUDE_API_KEY == "test-anthro-key"
    with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-claude-key"}, clear=True):
        settings2 = Settings()
        assert settings2.ANTHROPIC_API_KEY == "test-claude-key"
        assert settings2.CLAUDE_API_KEY == "test-claude-key"


def test_openai_api_key_aliases():
    """OPENAI_API_KEY and OPENAI_KEY should be recognized as aliases."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"}):
        settings = Settings()
        assert settings.OPENAI_API_KEY == "test-openai-key"
        assert settings.OPENAI_KEY == "test-openai-key"
    with patch.dict(os.environ, {"OPENAI_KEY": "test-openai-alt-key"}, clear=True):
        settings2 = Settings()
        assert settings2.OPENAI_API_KEY == "test-openai-alt-key"
        assert settings2.OPENAI_KEY == "test-openai-alt-key"


def test_dalle_api_key_aliases():
    """DALL_E_API_KEY and OPENAI_API_KEY should be recognized as aliases."""
    with patch.dict(os.environ, {"DALL_E_API_KEY": "test-dalle-key"}):
        settings = Settings()
        assert settings.DALL_E_API_KEY == "test-dalle-key"
        # It also aliases OPENAI_API_KEY, so OPENAI_API_KEY should also be test-dalle-key
        assert settings.OPENAI_API_KEY == "test-dalle-key"
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-for-dalle"}, clear=True):
        settings2 = Settings()
        assert settings2.DALL_E_API_KEY == "test-openai-for-dalle"
        assert settings2.OPENAI_API_KEY == "test-openai-for-dalle"


def test_get_gemini_api_key_method():
    """get_gemini_api_key() should return the configured value or empty string."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "method-test-key"}):
        settings = Settings()
        assert settings.get_gemini_api_key() == "method-test-key"
    with patch.dict(os.environ, {"GOOGLE_GENAI_API_KEY": "method-test-google"}, clear=True):
        settings2 = Settings()
        assert settings2.get_gemini_api_key() == "method-test-google"
    with patch.dict(os.environ, {}, clear=True):
        settings3 = Settings()
        # Should fall back to empty string via the method's logic
        assert settings3.get_gemini_api_key() == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])