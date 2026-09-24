import os
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.monitoring.sentry import init_sentry
from src.api.middleware.error_handler import ErrorHandlerMiddleware

@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    # Set a dummy SENTRY_DSN for testing and keep it active during the test
    patcher = patch.dict(os.environ, {"SENTRY_DSN": "https://dummy@dummy.ng/0"})
    patcher.start()
    try:
        init_sentry(app)
        @app.get("/trigger-error")
        def trigger_error():
            raise RuntimeError("Test error")
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        patcher.stop()

@patch("src.monitoring.sentry.sentry_sdk.capture_exception")
def test_sentry_captures_exception(mock_capture, client):
    # Call the endpoint that raises an exception
    try:
        client.get("/trigger-error")
    except RuntimeError:
        # The exception is expected to be raised by the Sentry middleware after capturing
        pass
    # Check that Sentry's capture_exception was called
    mock_capture.assert_called_once()