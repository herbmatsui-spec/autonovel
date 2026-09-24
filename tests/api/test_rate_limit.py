import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.api.middleware.rate_limit import RateLimitMiddleware

@pytest.fixture
def client():
    app = FastAPI()
    # Set a low rate limit for testing: 5 requests per minute
    app.add_middleware(RateLimitMiddleware, requests_per_minute=5)
    
    @app.post("/api/generate", status_code=202)
    def generate():
        return {"job_id": "test_job"}
    
    return TestClient(app)

def test_rate_limit_allows_n_requests(client):
    test_payload = {"title": "Test"}
    # Make 5 requests (should be allowed)
    for i in range(5):
        resp = client.post("/api/generate", json=test_payload)
        assert resp.status_code == 202, f"Request {i+1} failed with {resp.status_code}"
    # 6th request should be rate limited
    with pytest.raises(HTTPException) as exc_info:
        client.post("/api/generate", json=test_payload)
    assert exc_info.value.status_code == 429