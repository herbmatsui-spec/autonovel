def test_get_rate_limit_key():
    import hashlib
    from src.backend.auth import APIKeyService
    s = APIKeyService(allowed_keys=["test-key-12345"])
    expected_hash = hashlib.sha256(b"test-key-12345").hexdigest()
    assert s.get_rate_limit_key("test-key-12345") == f"apikey:{expected_hash}"
