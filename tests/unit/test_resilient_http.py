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


@pytest.mark.asyncio
async def test_resilient_http_put_method():
    """PUT メソッドが正しく動作することの検証。"""
    client = ResilientHttpClient(
        name="test_http_put",
        retry_policy=RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=3),
    )

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        resp = await client.put("http://example.com/api/resource", json={"id": 1})

        assert resp.status_code == 200
        mock_req.assert_called_once_with("PUT", "http://example.com/api/resource", json={"id": 1})

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_delete_method():
    """DELETE メソッドが正しく動作することの検証。"""
    client = ResilientHttpClient(
        name="test_http_delete",
        retry_policy=RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=3),
    )

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 204

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        resp = await client.delete("http://example.com/api/resource/1")

        assert resp.status_code == 204
        mock_req.assert_called_once_with("DELETE", "http://example.com/api/resource/1")

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_all_retries_fail_raises_last_exception():
    """全リトライ失敗時に最後の例外が再送出されることの検証。"""
    client = ResilientHttpClient(
        name="test_http_all_fail",
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=5),
    )

    err_resp = MagicMock(spec=httpx.Response)
    err_resp.status_code = 500
    err_resp.request = MagicMock()

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = err_resp

        with pytest.raises(httpx.HTTPStatusError):
            await client.get("http://example.com/api")

        assert mock_req.call_count == 3
        assert client.circuit_breaker.failure_count == 3

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_request_error_triggers_retry():
    """ネットワークエラー (RequestError) がリトリガーされることの検証。"""
    client = ResilientHttpClient(
        name="test_http_req_error",
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False),
        cb_config=CircuitBreakerConfig(failure_threshold=5),
    )

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(httpx.RequestError, match="Connection failed"):
            await client.post("http://example.com/api")

        assert mock_req.call_count == 3

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_retryable_status_code_config():
    """設定されたリトライ対象ステータスコードでリトライされることの検証。"""
    client = ResilientHttpClient(
        name="test_http_retryable",
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            retryable_status_codes={502, 503},
        ),
        cb_config=CircuitBreakerConfig(failure_threshold=5),
    )

    # 502 はリトライ対象
    err_resp_502 = MagicMock(spec=httpx.Response)
    err_resp_502.status_code = 502
    err_resp_502.request = MagicMock()

    ok_resp = MagicMock(spec=httpx.Response)
    ok_resp.status_code = 200

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [err_resp_502, ok_resp]
        resp = await client.get("http://example.com/api")
        assert resp.status_code == 200
        assert mock_req.call_count == 2

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_non_retryable_status_code_no_retry():
    """リトライ対象外ステータスコードでは即座に返ることの検証。"""
    client = ResilientHttpClient(
        name="test_http_no_retry",
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            retryable_status_codes={500},  # 400は含まない
        ),
        cb_config=CircuitBreakerConfig(failure_threshold=5),
    )

    err_resp_400 = MagicMock(spec=httpx.Response)
    err_resp_400.status_code = 400
    err_resp_400.request = MagicMock()

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = err_resp_400
        resp = await client.get("http://example.com/api")
        assert resp.status_code == 400
        assert mock_req.call_count == 1  # リトライなし

    await client.close()


@pytest.mark.asyncio
async def test_resilient_http_close_closes_underlying_client():
    """close() が内部クライアントを正しく閉じることの検証。"""
    client = ResilientHttpClient(
        name="test_http_close",
        retry_policy=RetryPolicy(max_attempts=1),
    )

    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_awaited_once()


@pytest.mark.asyncio
async def test_resilient_http_client_is_closed_after_close():
    """close() 後にクライアントが閉じられていることの検証。"""
    client = ResilientHttpClient(
        name="test_http_closed",
        retry_policy=RetryPolicy(max_attempts=1),
    )
    await client.close()
    assert client.client.is_closed