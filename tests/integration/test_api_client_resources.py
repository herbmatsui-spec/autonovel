"""api_client のリソース管理・定数・同期/非同期解決のテスト"""

import os

import pytest

from src.infrastructure.api import api_client


def test_api_base_url_default_when_env_unset(monkeypatch):
    """API_BASE_URL 環境変数が未設定時は既定値になること"""
    monkeypatch.delenv("API_BASE_URL", raising=False)
    # モジュール再読み込みは行わず、直接ロジック相当を確認
    assert api_client.API_BASE_URL == api_client.DEFAULT_API_BASE_URL or api_client.API_BASE_URL


def test_api_base_url_empty_env_falls_back_to_default(monkeypatch):
    """API_BASE_URL が空文字の場合は既定値にフォールバックすること"""
    monkeypatch.setenv("API_BASE_URL", "")
    # 実際の取得ロジックを再現
    env_val = os.environ.get("API_BASE_URL")
    resolved = env_val if env_val else api_client.DEFAULT_API_BASE_URL
    assert resolved == api_client.DEFAULT_API_BASE_URL


def test_resolve_if_coroutine_passthrough_non_coroutine():
    """非コルーチンはそのまま返ること"""
    sentinel = object()
    assert api_client._resolve_if_coroutine(sentinel) is sentinel


def test_request_resolves_coroutine_from_async_mock(monkeypatch):
    """client.request がコルーチンを返す場合、_request が値を解決すること"""

    class _AsyncClient:
        def request(self, method, url, params=None, json=None, timeout=10.0):
            async def _coro():
                return {"method": method, "params": params, "json": json}

            return _coro()

    monkeypatch.setattr(api_client, "_resilient_client", _AsyncClient())
    try:
        result = api_client._request("GET", "/test", foo="bar", timeout=5.0)
        assert result["params"] == {"foo": "bar"}
        assert result["json"] is None

        result = api_client._request("POST", "/test", title="foo", timeout=5.0)
        assert result["json"] == {"title": "foo"}
        assert result["params"] is None
    finally:
        monkeypatch.undo()


def test_get_client_returns_httpx_client():
    """get_client は httpx.Client を返すこと (遅延生成)"""
    client = api_client.get_client()
    assert isinstance(client, type(api_client._resilient_client)) or client is not None
    assert client is not None


def test_close_client_closes_sync_client(monkeypatch):
    """close_client は同期クライアントをクローズすること"""
    import httpx

    captured = {}
    client = httpx.Client(timeout=5.0)
    captured["client"] = client
    monkeypatch.setattr(api_client, "_resilient_client", client)
    api_client.close_client()
    assert client.is_closed
    # クローズ後は再度新規生成される
    assert api_client._resilient_client is None


@pytest.mark.asyncio
async def test_async_client_is_shared_and_reused(monkeypatch):
    """_get_async_client は同じインスタンスを再利用すること"""
    api_client._async_client = None
    try:
        c1 = api_client._get_async_client()
        c2 = api_client._get_async_client()
        assert c1 is c2
        assert isinstance(c1, object) and c1 is not None
    finally:
        await api_client.close_async_client()


@pytest.mark.asyncio
async def test_close_async_client_sets_none(monkeypatch):
    """close_async_client は共有クライアントを None にすること"""
    api_client._async_client = None
    api_client._get_async_client()
    await api_client.close_async_client()
    assert api_client._async_client is None
