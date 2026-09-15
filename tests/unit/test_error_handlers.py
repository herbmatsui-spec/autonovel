"""Tests for error handlers in src.backend.error_handlers."""

import pytest
import json
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from src.backend.error_handlers import (
    register_error_handlers,
    http_exception_handler,
    validation_exception_handler,
)
from src.backend.config import settings


@pytest.mark.asyncio
async def test_http_exception_handler_rfc7807():
    dummy_request = MagicMock()
    dummy_request.url.path = "/api/test-endpoint"
    exc = HTTPException(status_code=404, detail="Resource not found")

    response = await http_exception_handler(dummy_request, exc)
    assert response.status_code == 404
    body = json.loads(response.body.decode("utf-8"))
    assert body["title"] == "Resource not found"
    assert body["status"] == 404
    assert body["detail"] == "Resource not found"
    assert body["instance"] == "/api/test-endpoint"
    assert "errors/http-404" in body["type"]


@pytest.mark.asyncio
async def test_http_exception_handler_non_string_detail():
    dummy_request = MagicMock()
    dummy_request.url.path = "/api/test-endpoint"
    exc = HTTPException(status_code=400, detail={"key": "value"})

    response = await http_exception_handler(dummy_request, exc)
    assert response.status_code == 400
    body = json.loads(response.body.decode("utf-8"))
    # 非文字列 detail は title が "HTTP Error" にフォールバックする
    assert body["title"] == "HTTP Error"


@pytest.mark.asyncio
async def test_validation_exception_handler():
    dummy_request = MagicMock()
    dummy_request.url.path = "/api/test-endpoint"
    # RequestValidationError の軽量スタブ
    exc = MagicMock()
    exc.errors.return_value = [
        {"loc": ("body", "title"), "msg": "field required"},
    ]

    response = await validation_exception_handler(dummy_request, exc)
    assert response.status_code == 422
    body = json.loads(response.body.decode("utf-8"))
    assert "検証に失敗" in body["title"]
    assert body["invalid_params"][0]["name"] == "body -> title"
    assert "field required" in body["invalid_params"][0]["reason"]


def test_register_error_handlers():
    app = MagicMock()
    register_error_handlers(app)
    assert app.add_exception_handler.call_count == 2
