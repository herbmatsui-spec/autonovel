import pytest

from src.shared.result import Result


def test_ok_value():
    r = Result.ok(42)
    assert r.is_ok and r.value == 42


def test_err_value():
    r = Result.err(ValueError("x"))
    assert r.is_err


def test_map_success():
    r = Result.ok(2).map(lambda x: x * 3)
    assert r.value == 6


def test_map_err_leaves_ok_unchanged():
    r = Result.ok(42).map_err(lambda e: ValueError("mapped"))
    assert r.is_ok and r.value == 42


def test_unwrap_raises():
    r = Result.err(ValueError("x"))
    with pytest.raises(ValueError) as exc_info:
        r.unwrap()
    assert str(exc_info.value) == "x"


def test_map_on_err_preserves_error():
    err = ValueError("original")
    r = Result.err(err).map(lambda x: x * 2)
    assert r.is_err and r.error is err


def test_map_err_on_err():
    err = ValueError("original")
    mapped_err = RuntimeError("mapped")
    r = Result.err(err).map_err(lambda e: mapped_err)
    assert r.is_err and r.error is mapped_err
