import os
import pytest


def test_get_allowed_origins_from_env():
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins


def test_get_allowed_origins_default():
    if "CORS_ALLOWED_ORIGINS" in os.environ:
        del os.environ["CORS_ALLOWED_ORIGINS"]
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:5173" in origins
    assert "http://localhost:8501" in origins
