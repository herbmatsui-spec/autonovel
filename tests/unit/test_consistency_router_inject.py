from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)

def test_consistency_injection_endpoint():
    # We don't have real data, but we can test that the endpoint returns 200 and JSON with injection key.
    # Since there is no workspace file, the injection will likely be empty string.
    response = client.get("/api/consistency/1/inject?ep_num=1")
    assert response.status_code == 200
    data = response.json()
    assert "injection" in data
    assert isinstance(data["injection"], str)
    # Optionally, we can also test that it's empty (since no files)
    # But we won't assert empty because there might be some default? Actually with no files, findings will be empty, injection empty.
    # Let's assert it's a string (already done).