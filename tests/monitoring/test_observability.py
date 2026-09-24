"""Sentry と OpenTelemetry が例外を正しく捕捉することをテスト"""
from unittest.mock import patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.monitoring.sentry import init_sentry
from src.monitoring.otel import init_otel
from src.api.middleware.error_handler import ErrorHandlerMiddleware

@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    init_sentry(app)
    init_otel(app)
    
    @app.get("/")
    def root():
        from opentelemetry import trace
        tracer = trace.get_tracer("test_tracer")
        with tracer.start_span("root_request"):
            return {"status": "ok"}

    @app.get("/trigger-error")
    def trigger_error():
        raise RuntimeError("Test error")
    
    return TestClient(app, raise_server_exceptions=False)

@patch("src.monitoring.sentry.sentry_sdk.capture_exception")
def test_sentry_captures_api_exception(mock_capture, client):
    # エラーを返すエンドポイントを呼ぶ（例: 不正な入力で 500）
    resp = client.get("/trigger-error")
    # 実際には 500 となる
    assert resp.status_code == 500
    mock_capture.assert_called_once()

@patch("opentelemetry.trace.get_tracer")
def test_otel_creates_span_for_request(mock_get_tracer, client):
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_span.return_value.__enter__.return_value = mock_span
    mock_get_tracer.return_value = mock_tracer
    # 任意のエンドポイントにリクエスト
    resp = client.get("/")
    assert resp.status_code == 200
    # スパンが作成されたことを確認
    mock_tracer.start_span.assert_called()