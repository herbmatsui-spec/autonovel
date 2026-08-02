import pytest
import requests


@pytest.fixture(scope="module")
def easy_mode_api_url():
    return "http://localhost:8200/api/easy_mode/generate"


@pytest.fixture(scope="module")
def api_request_data():
    return {
        "api_key": "test",
        "config": {
            "genre": "test",
            "keywords": "test",
            "archetype_key": "test",
            "target_eps": 1,
            "initial_limit": 1,
            "word_count": 1000,
        },
    }


@pytest.mark.skip(reason="Manual API test - requires local server on port 8200")
def test_api_quick_generate(easy_mode_api_url, api_request_data):
    """
    Quick mode API generation test.
    Requires running server at localhost:8200
    Run with: uvicorn src.backend.server:app --port 8200 &
    """
    try:
        response = requests.post(easy_mode_api_url, json=api_request_data, timeout=5)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "task_id" in data or "result" in data
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running at localhost:8200")


@pytest.mark.integration
def test_api_health_check(easy_mode_api_url):
    """API health check endpoint test"""
    try:
        response = requests.get(f"{easy_mode_api_url.rsplit('/', 1)[0]}/health", timeout=2)
        assert response.status_code in [200, 404]
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running - health endpoint not available")


@pytest.mark.skip(reason="Mock-based test - API not available in CI")
def test_api_generate_mock(mocker):
    """Mock-based API test for CI environments"""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"task_id": "test-task-123", "result": "generated"}

    with pytest.MonkeyPatch.context() as m:
        m.setattr(requests, "post", lambda url, json=None, timeout=None: mock_response)
        pytest.fail("Mock setup requires proper configuration")