from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.shared.circuit_breaker import CircuitBreakerConfig, CircuitState
from src.shared.resilient_http import CircuitBreakerOpenException, ResilientHttpClient
from src.shared.retry_policy import RetryPolicy


@pytest.mark.asyncio
async def test_resilient_http_success():
    """正常リクエストが成功しレスポンスを返すことの検証。"""
    client = ResilientHttpClient(
        name="test_http",
        retry_policy=RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=3),
    )

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        resp = await client.get("http://example.com/api")

        assert resp.status_code == 200
        assert mock_req.call_count == 1
        assert client.circuit_breaker.state == CircuitState.CLOSED

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_retry_and_succeed():
    """500エラー後にリトライして成功することの検証。"""
    client = ResilientHttpClient(
        name="test_http_retry",
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=5),
    )

    err_resp = MagicMock(spec=httpx.Response)
    err_resp.status_code = 500
    err_resp.request = MagicMock()

    ok_resp = MagicMock(spec=httpx.Response)
    ok_resp.status_code = 200

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [err_resp, ok_resp]
        resp = await client.post("http://example.com/api", json={"test": 1})

        assert resp.status_code == 200
        assert mock_req.call_count == 2

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_circuit_open_blocks_request():
    """サーキットブレーカーが OPEN の場合にリクエストが即時ブロックされることの検証。"""
    client = ResilientHttpClient(
        name="test_http_open",
        retry_policy=RetryPolicy(max_attempts=1, base_delay=0.01),
        cb_config=CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60.0),
    )

    # 失敗させて OPEN 状態にする
    client.circuit_breaker.record_failure()
    assert client.circuit_breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenException):
        await client.get("http://example.com/api")

    await client.close()
