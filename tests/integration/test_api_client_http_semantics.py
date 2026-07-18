"""api_client の HTTP 语义テスト"""
from unittest.mock import patch, MagicMock, AsyncMock
import streamlit_app.api_client as api_client


def test_get_request_uses_params_not_json():
    """GETリクエストはkwargsをparamsとして渡し、jsonはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        async def fake_request(method, path, params=None, json=None, timeout=10.0):
            return {"method": method, "params": params, "json": json, "timeout": timeout}

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("GET", "/test", foo="bar", timeout=5.0)
        assert result["params"] == {"foo": "bar"}
        assert result["json"] is None
        assert result["timeout"] == 5.0


def test_post_request_uses_json_not_params():
    """POSTリクエストはkwargsをjsonとして渡し、paramsはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        async def fake_request(method, path, params=None, json=None, timeout=10.0):
            return {"method": method, "params": params, "json": json, "timeout": timeout}

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("POST", "/test", title="foo", timeout=10.0)
        assert result["json"] == {"title": "foo"}
        assert result["params"] is None
        assert result["timeout"] == 10.0


def test_delete_request_uses_params_not_json():
    """DELETEリクエストはkwargsをparamsとして渡し、jsonはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        async def fake_request(method, path, params=None, json=None, timeout=10.0):
            return {"method": method, "params": params, "json": json, "timeout": timeout}

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("DELETE", "/test/123", timeout=5.0)
        assert result["params"] == {}
        assert result["json"] is None
        assert result["timeout"] == 5.0


def test_delete_request_uses_params_not_json():
    """DELETEリクエストはkwargsをparamsとして渡し、jsonはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        async def fake_request(method, path, params=None, json=None, timeout=10.0):
            return {"method": method, "params": params, "json": json, "timeout": timeout}

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("DELETE", "/test/123", timeout=5.0)
        assert result["params"] == {}
        assert result["json"] is None
        assert result["timeout"] == 5.0
