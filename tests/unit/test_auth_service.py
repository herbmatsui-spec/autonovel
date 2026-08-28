import os
import pytest
from src.backend.auth import APIKeyService, get_api_key_service, reset_api_key_service, validate_api_key_or_raise

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Ensure environment clean for each test
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("ALLOWED_API_KEYS", raising=False)

def test_service_disabled_non_production(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    service = APIKeyService(disabled=True)
    assert service.disabled is True
    # When disabled and not production, any key is accepted
    assert service.validate("anykey") is True

def test_service_disabled_production(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    service = APIKeyService(disabled=True)
    assert service.disabled is True
    # In production, disabled should still reject keys
    assert service.validate("anykey") is False

def test_service_allowed_keys(monkeypatch):
    monkeypatch.setenv("ALLOWED_API_KEYS", "key1, key2")
    reset_api_key_service()
    service = get_api_key_service()
    assert service.validate("key1") is True
    assert service.validate("wrong") is False

def test_validate_api_key_or_raise(monkeypatch):
    monkeypatch.setenv("ALLOWED_API_KEYS", "secret")
    reset_api_key_service()
    # valid key passes
    assert validate_api_key_or_raise("secret") == "secret"
    # invalid key raises AppError (subclass of Exception)
    with pytest.raises(Exception) as exc:
        validate_api_key_or_raise("bad")
    assert getattr(exc.value, "error_code", None) == "FORBIDDEN"
    assert getattr(exc.value, "status_code", None) == 403

