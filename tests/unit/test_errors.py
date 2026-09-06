import pytest

from src.shared.errors import (
    GenerationError,
    LLMTimeoutError,
    LLMRateLimitError,
    AuditFailureError,
    PipelineCancelledError,
)


class TestGenerationError:
    def test_generation_error_with_message_only(self):
        error = GenerationError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.cause is None

    def test_generation_error_with_cause(self):
        cause = ValueError("root cause")
        error = GenerationError("Operation failed", cause=cause)
        assert str(error) == "Operation failed"
        assert error.cause is cause
        assert isinstance(error.cause, ValueError)

    def test_generation_error_is_exception(self):
        error = GenerationError("test")
        assert isinstance(error, Exception)

    def test_generation_error_chaining(self):
        try:
            raise ValueError("original")
        except ValueError as e:
            gen_error = GenerationError("wrapped", cause=e)
            assert gen_error.cause is e


class TestLLMTimeoutError:
    def test_llm_timeout_error_inherits_from_generation_error(self):
        error = LLMTimeoutError("timeout")
        assert isinstance(error, GenerationError)
        assert isinstance(error, Exception)

    def test_llm_timeout_error_with_cause(self):
        cause = TimeoutError("connection timeout")
        error = LLMTimeoutError("LLM request timed out", cause=cause)
        assert error.cause is cause


class TestLLMRateLimitError:
    def test_llm_rate_limit_error_inherits_from_generation_error(self):
        error = LLMRateLimitError("rate limited")
        assert isinstance(error, GenerationError)
        assert isinstance(error, Exception)


class TestAuditFailureError:
    def test_audit_failure_error_inherits_from_generation_error(self):
        error = AuditFailureError("audit failed")
        assert isinstance(error, GenerationError)
        assert isinstance(error, Exception)


class TestPipelineCancelledError:
    def test_pipeline_cancelled_error_inherits_from_generation_error(self):
        error = PipelineCancelledError("pipeline cancelled")
        assert isinstance(error, GenerationError)
        assert isinstance(error, Exception)

    def test_pipeline_cancelled_error_with_cause(self):
        cause = KeyboardInterrupt()
        error = PipelineCancelledError("cancelled by user", cause=cause)
        assert error.cause is cause
        assert isinstance(error.cause, KeyboardInterrupt)