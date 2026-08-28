import os
import pytest

from src.backend.auth import APIKeyService, get_api_key_service, reset_api_key_service, validate_api_key_or_raise

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Ensure a clean environment for each test
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("ALLOWED_API_KEYS", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

def test_validate_without_allowed_keys_fails(monkeypatch):
    # No ALLOWED_API_KEYS set, environment is development
    monkeypatch.setenv("ENVIRONMENT", "development")
    reset_api_key_service()
    service = get_api_key_service()
    # A normal key should be rejected
    assert service.validate("normal-key") is False
    # The fallback for "test" keys does not apply to non‑test keys
    assert service.validate("another-key") is False

def test_test_key_allowed_when_not_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    reset_api_key_service()
    service = get_api_key_service()
    # "test" prefixed key should be accepted even without ALLOWED_API_KEYS
    assert service.validate("test-key-123") is True

def test_test_key_rejected_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    reset_api_key_service()
    service = get_api_key_service()
    assert service.validate("test-key-123") is False

def test_validate_api_key_or_raise_with_test_key_non_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    # Ensure ALLOWED_API_KEYS is empty
    monkeypatch.delenv("ALLOWED_API_KEYS", raising=False)
    reset_api_key_service()
    # Should accept the test key
    assert validate_api_key_or_raise("test-allowed") == "test-allowed"

def test_validate_api_key_or_raise_with_test_key_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOWED_API_KEYS", raising=False)
    reset_api_key_service()
    with pytest.raises(Exception) as exc:
        validate_api_key_or_raise("test-should-fail")
    assert getattr(exc.value, "error_code", None) == "FORBIDDEN"

