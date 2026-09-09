"""Tests for Unified Environment Variable Resolution & API Key Aliases (Phase 4 / Steps 37-48)."""
import os
import pytest
from src.backend.config import Settings
from src.dependencies import _get_api_key
from src.services.image_service import ImageService


def test_gemini_key_alias_with_google_genai_api_key(monkeypatch):
    """Step 37: When only GOOGLE_GENAI_API_KEY is set, GEMINI_API_KEY is loaded via AliasChoices."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "test-google-genai-key-12345")

    s = Settings()
    assert s.GEMINI_API_KEY == "test-google-genai-key-12345"
    assert s.get_gemini_api_key() == "test-google-genai-key-12345"


def test_gemini_key_alias_with_gemini_api_key(monkeypatch):
    """Step 37: When GEMINI_API_KEY is set, it takes priority and loads correctly."""
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-67890")

    s = Settings()
    assert s.GEMINI_API_KEY == "test-gemini-key-67890"
    assert s.get_gemini_api_key() == "test-gemini-key-67890"


def test_claude_and_openai_aliases(monkeypatch):
    """Step 42: CLAUDE_API_KEY and OPENAI_KEY aliases resolve correctly."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_API_KEY", "test-claude-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_KEY", "test-openai-key")

    s = Settings()
    assert s.ANTHROPIC_API_KEY == "test-claude-key"
    assert s.OPENAI_API_KEY == "test-openai-key"


def test_dependencies_get_api_key(monkeypatch):
    """Step 39, 46: dependencies._get_api_key resolves key via unified settings."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-dep-key")
    from src.backend.config import settings
    settings.GEMINI_API_KEY = "test-dep-key"

    key = _get_api_key()
    assert key == "test-dep-key"


def test_image_service_key_resolution(monkeypatch):
    """Step 40, 47: ImageService auto-resolves key from settings/env when api_key is None."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-image-key")
    from src.backend.config import settings
    settings.GEMINI_API_KEY = "test-image-key"

    # Instantiate without explicitly passing api_key
    svc = ImageService()
    assert svc.client is not None
