import pytest

from src.shared.result import Result


class TestResult:
    def test_is_ok_returns_true_for_ok_result(self):
        result = Result.ok(42)
        assert result.is_ok is True
        assert result.is_err is False

    def test_is_ok_returns_false_for_err_result(self):
        result = Result.err(ValueError("error"))
        assert result.is_ok is False
        assert result.is_err is True

    def test_ok_creates_result_with_value(self):
        result = Result.ok("success")
        assert result.value == "success"
        assert result.error is None

    def test_err_creates_result_with_error(self):
        error = ValueError("failed")
        result = Result.err(error)
        assert result.error is error
        assert result.value is None

    def test_unwrap_returns_value_for_ok(self):
        result = Result.ok(100)
        assert result.unwrap() == 100

    def test_unwrap_raises_error_for_err(self):
        error = RuntimeError("boom")
        result = Result.err(error)
        with pytest.raises(RuntimeError, match="boom"):
            result.unwrap()

    def test_map_transforms_ok_value(self):
        result = Result.ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok
        assert mapped.unwrap() == 10

    def test_map_preserves_error(self):
        error = ValueError("err")
        result = Result.err(error)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err
        assert mapped.error is error

    def test_map_err_transforms_error(self):
        error = ValueError("original")
        result = Result.err(error)
        mapped = result.map_err(lambda e: RuntimeError(f"wrapped: {e}"))
        assert mapped.is_err
        assert isinstance(mapped.error, RuntimeError)
        assert "original" in str(mapped.error)

    def test_map_err_preserves_ok_value(self):
        result = Result.ok("value")
        mapped = result.map_err(lambda e: RuntimeError("new"))
        assert mapped.is_ok
        assert mapped.unwrap() == "value"

    def test_chained_operations(self):
        result = Result.ok(3)
        final = result.map(lambda x: x + 1).map(lambda x: x * 2).map_err(lambda e: e)
        assert final.is_ok
        assert final.unwrap() == 8

    def test_chained_operations_with_error(self):
        result = Result.err(ValueError("fail"))
        final = result.map(lambda x: x + 1).map_err(lambda e: RuntimeError("wrapped"))
        assert final.is_err
        assert isinstance(final.error, RuntimeError)

    def test_generic_type_preservation(self):
        result = Result.ok([1, 2, 3])
        mapped = result.map(lambda lst: len(lst))
        assert mapped.is_ok
        assert isinstance(mapped.unwrap(), int)
        assert mapped.unwrap() == 3