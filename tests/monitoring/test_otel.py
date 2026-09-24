import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.monitoring.otel import init_otel

@pytest.fixture
def client():
    app = FastAPI()
    init_otel(app)
    
    @app.get("/")
    def read_root():
        from opentelemetry import trace
        tracer = trace.get_tracer("test_otel")
        with tracer.start_span("root_span"):
            return {"Hello": "World"}
    
    return TestClient(app)

@patch("opentelemetry.trace.get_tracer")
def test_otel_creates_span_for_request(mock_get_tracer, client):
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_span.return_value.__enter__.return_value = mock_span
    mock_get_tracer.return_value = mock_tracer
    
    # Make a request to the root endpoint
    response = client.get("/")
    assert response.status_code == 200
    
    # Check that a span was started
    mock_get_tracer.assert_called()
    mock_tracer.start_span.assert_called()