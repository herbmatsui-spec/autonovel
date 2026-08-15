def test_get_rate_limit_key():
    from src.backend.auth import APIKeyService
    s = APIKeyService(allowed_keys=["test-key-12345"])
    assert s.get_rate_limit_key("test-key-12345") == "apikey:test-key"
