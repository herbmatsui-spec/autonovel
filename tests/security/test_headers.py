import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.security.headers import SecurityHeadersMiddleware

@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/")
    def read_root():
        return {"Hello": "World"}
    
    return TestClient(app)

def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-xss-protection"] == "1; mode=block"
    assert "content-security-policy" in resp.headers