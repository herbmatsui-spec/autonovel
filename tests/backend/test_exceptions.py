from src.backend.exceptions import (
    BackendError,
    CacheError,
    CacheMiss,
    DatabaseError,
    RateLimitExceeded,
)


def test_hierarchy():
    assert issubclass(RateLimitExceeded, BackendError)
    assert issubclass(CacheError, BackendError)
    assert issubclass(CacheMiss, BackendError)
    assert issubclass(DatabaseError, BackendError)


def test_cause_chain():
    cause = ValueError("x")
    err = DatabaseError("db failed", cause=cause)
    assert err.cause is cause
    assert "db failed" in str(err)
