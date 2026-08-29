import logging

from src.backend.error_utils import log_exception


def test_log_exception_emits_error(caplog):
    logger = logging.getLogger("test_err")
    try:
        raise ValueError("boom")
    except ValueError as e:
        with caplog.at_level(logging.ERROR):
            log_exception(logger, "failed", e)
    assert "failed" in caplog.text
    assert "boom" in caplog.text
