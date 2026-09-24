import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.middleware.error_handler import ErrorHandlerMiddleware

@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    
    @app.get("/trigger-error")
    def trigger_error():
        raise RuntimeError("Test error")
    
    return TestClient(app)

def test_returns_generic_error_message(client):
    resp = client.get("/trigger-error")
    assert resp.status_code == 500
    data = resp.json()
    assert "message" in data
    assert data["message"] == "Internal Server Error"
    # スタックトレースが含まれていないこと
    assert "traceback" not in data
    assert "File" not in str(data)

def test_404_returns_default_message(client):
    resp = client.get("/nonexistent")
    # Note: 404 is not handled by our middleware because it doesn't raise an exception.
    # FastAPI returns a default 404 response. We can check that it doesn't contain stack trace.
    assert resp.status_code == 404
    data = resp.json()
    # The default FastAPI 404 response has a detail field.
    assert "detail" in data
    # Ensure no stack trace in the detail
    assert "traceback" not in str(data)
    assert "File" not in str(data)