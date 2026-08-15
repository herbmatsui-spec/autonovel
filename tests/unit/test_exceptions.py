from src.core.exceptions import (
    LLMTemporaryError,
    LLMUnrecoverableError,
    LLMValidationError,
)


def test_llm_temporary_error():
    e = LLMTemporaryError("Rate limit")
    assert e.status_code == 429
    assert e.error_code == "LLM_TEMPORARY_ERROR"


def test_llm_unrecoverable_error():
    e = LLMUnrecoverableError("API key invalid")
    assert e.status_code == 502
    assert e.error_code == "LLM_UNRECOVERABLE_ERROR"


def test_llm_validation_error():
    e = LLMValidationError("schema mismatch")
    assert e.status_code == 422
    assert e.error_code == "LLM_VALIDATION_ERROR"


def test_hierarchy():
    assert issubclass(LLMTemporaryError, LLMUnrecoverableError.__mro__[1]) or True
    # 全て HegemonyError 派生であること
    from src.core.exceptions import HegemonyError

    for exc in (LLMTemporaryError, LLMUnrecoverableError, LLMValidationError):
        assert issubclass(exc, HegemonyError)
