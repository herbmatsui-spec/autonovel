"""Unit tests for src/infrastructure/api/api_client.py - Async HTTP API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.infrastructure.api.api_client import (
    get_client,
    _request,
    _async_request,
    _get_async_client,
    close_async_client,
    close_client,
    list_books,
    get_book,
    delete_book,
    get_plots,
    get_chapters,
    get_bible,
    get_opt_history,
    get_task_status,
    stop_task,
    generate_easy,
    generate_episodes,
    plan_generation,
    retry_failed_episodes,
    expand_plots,
    rebuild_plots,
    critique_optimize,
    import_chapter,
    generate_marketing,
    analyze_style_dna,
    create_chapter,
    delete_chapter,
    get_issues,
    resolve_issue,
    save_pending_patch,
    get_pending_patches,
    approve_patch,
    reject_patch,
    get_prompt_versions,
    rollback_prompt_version,
    audit_producer_plan,
    export_package,
    API_BASE_URL,
    _PARAMS_METHODS,
    _JSON_METHODS,
)


class TestConstants:
    """Tests for module constants."""

    def test_api_base_url_default(self):
        """Test default API base URL."""
        assert API_BASE_URL == "http://localhost:8200/api"

    def test_params_methods(self):
        """Test PARAMS methods set."""
        assert "GET" in _PARAMS_METHODS
        assert "DELETE" in _PARAMS_METHODS
        assert "HEAD" in _PARAMS_METHODS
        assert "POST" not in _PARAMS_METHODS

    def test_json_methods(self):
        """Test JSON methods set."""
        assert "POST" in _JSON_METHODS
        assert "PUT" in _JSON_METHODS
        assert "PATCH" in _JSON_METHODS
        assert "GET" not in _JSON_METHODS


class TestSyncClient:
    """Tests for synchronous client functions."""

    def setup_method(self):
        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = None

    def test_get_client_creates_new(self):
        """Test get_client creates new client."""
        client = get_client()
        assert isinstance(client, httpx.Client)

    def test_get_client_returns_existing(self):
        """Test get_client returns existing client."""
        client1 = get_client()
        client2 = get_client()
        assert client1 is client2

    def test_get_client_uses_mock(self):
        """Test get_client uses mocked client."""
        import src.infrastructure.api.api_client as api_client
        mock_client = MagicMock()
        api_client._resilient_client = mock_client

        client = get_client()
        assert client is mock_client


class TestRequestRouting:
    """Tests for HTTP method routing logic."""

    def test_request_get_uses_params(self):
        """Test GET request uses params."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.request.return_value = mock_response

        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = mock_client

        with patch("src.infrastructure.api.api_client._resolve_if_coroutine", return_value=mock_response):
            result = _request("GET", "/test", param1="value1")

        call_args = mock_client.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[1]["params"] == {"param1": "value1"}
        assert call_args[1]["json"] is None

    def test_request_post_uses_json(self):
        """Test POST request uses json."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.request.return_value = mock_response

        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = mock_client

        with patch("src.infrastructure.api.api_client._resolve_if_coroutine", return_value=mock_response):
            result = _request("POST", "/test", data1="value1")

        call_args = mock_client.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["json"] == {"data1": "value1"}
        assert call_args[1]["params"] is None

    def test_request_delete_uses_params(self):
        """Test DELETE request uses params."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.request.return_value = mock_response

        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = mock_client

        with patch("src.infrastructure.api.api_client._resolve_if_coroutine", return_value=mock_response):
            result = _request("DELETE", "/test", id=123)

        call_args = mock_client.request.call_args
        assert call_args[1]["params"] == {"id": 123}
        assert call_args[1]["json"] is None

    def test_request_unknown_method_uses_params(self):
        """Test unknown method defaults to params."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.request.return_value = mock_response

        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = mock_client

        with patch("src.infrastructure.api.api_client._resolve_if_coroutine", return_value=mock_response):
            result = _request("UNKNOWN", "/test", param="value")

        call_args = mock_client.request.call_args
        assert call_args[1]["params"] == {"param": "value"}
        assert call_args[1]["json"] is None


class TestAsyncClient:
    """Tests for asynchronous client functions."""

    def setup_method(self):
        import src.infrastructure.api.api_client as api_client
        api_client._async_client = None

    @pytest.mark.asyncio
    async def test_get_async_client_creates_new(self):
        """Test _get_async_client creates new client."""
        client = _get_async_client()
        assert isinstance(client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_async_client_reuses(self):
        """Test _get_async_client reuses existing client."""
        client1 = _get_async_client()
        client2 = _get_async_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_async_client(self):
        """Test close_async_client."""
        client = _get_async_client()
        await close_async_client()

        import src.infrastructure.api.api_client as api_client
        assert api_client._async_client is None


class TestAsyncRequest:
    """Tests for _async_request function."""

    @pytest.mark.asyncio
    async def test_async_request_success(self):
        """Test successful async request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "ok"}

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.is_closed = False

        import src.infrastructure.api.api_client as api_client
        api_client._async_client = mock_client

        response = await _async_request("GET", "http://test/api/test")

        assert response == mock_response
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_request_connection_error(self):
        """Test async request with connection error."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")
        mock_client.is_closed = False

        import src.infrastructure.api.api_client as api_client
        api_client._async_client = mock_client

        with pytest.raises(Exception) as exc_info:
            await _async_request("GET", "http://test/api/test")

        assert "接続できません" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_request_timeout(self):
        """Test async request with timeout."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("Timeout")
        mock_client.is_closed = False

        import src.infrastructure.api.api_client as api_client
        api_client._async_client = mock_client

        with pytest.raises(Exception) as exc_info:
            await _async_request("GET", "http://test/api/test")

        assert "接続できません" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_request_http_error(self):
        """Test async request with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.is_closed = False

        import src.infrastructure.api.api_client as api_client
        api_client._async_client = mock_client

        with pytest.raises(Exception) as exc_info:
            await _async_request("GET", "http://test/api/test")

        assert "APIエラー" in str(exc_info.value)


class TestAPIMethods:
    """Tests for individual API method functions."""

    def setup_method(self):
        import src.infrastructure.api.api_client as api_client
        api_client._async_client = None

    @pytest.mark.asyncio
    async def test_list_books(self):
        """Test list_books."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Book 1"}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await list_books()

        assert result == [{"id": 1, "title": "Book 1"}]

    @pytest.mark.asyncio
    async def test_get_book(self):
        """Test get_book."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "title": "Book 1"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_book(1)

        assert result == {"id": 1, "title": "Book 1"}

    @pytest.mark.asyncio
    async def test_delete_book(self):
        """Test delete_book."""
        mock_response = MagicMock()
        mock_response.json.return_value = True

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await delete_book(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_plots(self):
        """Test get_plots."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Plot 1"}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_plots(1)

        assert result == [{"id": 1, "title": "Plot 1"}]

    @pytest.mark.asyncio
    async def test_get_chapters(self):
        """Test get_chapters."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Chapter 1"}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_chapters(1)

        assert result == [{"id": 1, "title": "Chapter 1"}]

    @pytest.mark.asyncio
    async def test_get_bible(self):
        """Test get_bible."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"settings": {}}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_bible(1)

        assert result == {"settings": {}}

    @pytest.mark.asyncio
    async def test_get_opt_history(self):
        """Test get_opt_history."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_opt_history(1)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """Test get_task_status success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"is_running": True, "progress": 50}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_task_status("task-123")

        assert result["is_running"] is True
        assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_get_task_status_error(self):
        """Test get_task_status error handling."""
        with patch("src.infrastructure.api.api_client._async_request", side_effect=Exception("Error")):
            result = await get_task_status("task-123")

        assert result["is_running"] is False
        assert "通信エラー" in result["error"]

    @pytest.mark.asyncio
    async def test_stop_task(self):
        """Test stop_task."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await stop_task("task-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_generate_easy(self):
        """Test generate_easy."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await generate_easy(
                api_key="key", config={}, genre="fantasy", keywords="test",
                archetype_key="hero", target_eps=10, initial_limit=5,
                word_count=2000, concept="test", tone_vibe=0.5
            )

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_generate_episodes(self):
        """Test generate_episodes."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await generate_episodes(
                api_key="key", config={}, book_id=1, write_from=1, write_to=5,
                passion=0.8, word_count=2000, do_refine=True,
                env_state={}, pipeline_mode=False
            )

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_plan_generation(self):
        """Test plan_generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await plan_generation(api_key="key", config={}, params={})

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_retry_failed_episodes(self):
        """Test retry_failed_episodes."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await retry_failed_episodes(
                api_key="key", config={}, book_id=1, passion=0.8, word_count=2000
            )

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_expand_plots(self):
        """Test expand_plots."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await expand_plots(
                api_key="key", config={}, book_id=1, gen_from=1, gen_to=10
            )

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_rebuild_plots(self):
        """Test rebuild_plots."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await rebuild_plots(api_key="key", config={}, params={})

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_critique_optimize(self):
        """Test critique_optimize."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await critique_optimize(api_key="key", config={}, book_id=1)

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_import_chapter(self):
        """Test import_chapter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await import_chapter(
                api_key="key", book_id=1, ep_num=1, import_text="text", do_refine=True
            )

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_generate_marketing(self):
        """Test generate_marketing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "task-123"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await generate_marketing(api_key="key", book_id=1, latest_ep=5)

        assert result == "task-123"

    @pytest.mark.asyncio
    async def test_analyze_style_dna(self):
        """Test analyze_style_dna."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"style": "web"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await analyze_style_dna(api_key="key", sample="sample text")

        assert result == {"style": "web"}

    @pytest.mark.asyncio
    async def test_create_chapter(self):
        """Test create_chapter."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await create_chapter(
                book_id=1, ep_num=1, title="Ch1", content="content",
                summary="sum", killer_phrase="kp", ai_insight="ai",
                world_state={}, trinity_review_log={}, created_at="2024-01-01"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_chapter(self):
        """Test delete_chapter."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await delete_chapter(1, 1)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_issues(self):
        """Test get_issues."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_issues(1)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_resolve_issue(self):
        """Test resolve_issue."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "resolved"}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await resolve_issue(1, "fix", "api_key")

        assert result == {"status": "resolved"}

    @pytest.mark.asyncio
    async def test_save_pending_patch(self):
        """Test save_pending_patch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await save_pending_patch(1, "type", "content", {})

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_get_pending_patches(self):
        """Test get_pending_patches."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_pending_patches(1)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_approve_patch(self):
        """Test approve_patch."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await approve_patch(1)

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_reject_patch(self):
        """Test reject_patch."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await reject_patch(1)

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_get_prompt_versions(self):
        """Test get_prompt_versions."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"version": 1}]

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await get_prompt_versions(1)

        assert result == [{"version": 1}]

    @pytest.mark.asyncio
    async def test_rollback_prompt_version(self):
        """Test rollback_prompt_version."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await rollback_prompt_version(1, 1)

        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_audit_producer_plan(self):
        """Test audit_producer_plan."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"score": 80}

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await audit_producer_plan(
                api_key="key", genre="fantasy", keywords="test",
                trend_memo="memo", sanctuary="sanc", originality_score=50
            )

        assert result == {"score": 80}

    @pytest.mark.asyncio
    async def test_export_package(self):
        """Test export_package."""
        mock_response = MagicMock()

        with patch("src.infrastructure.api.api_client._async_request", new_callable=AsyncMock) as mock_async_request:
            mock_async_request.return_value = mock_response
            result = await export_package(api_key="key", book_id=1)

        assert result == mock_response


class TestCloseClient:
    """Tests for close_client function."""

    def test_close_client(self):
        """Test close_client closes both clients."""
        import src.infrastructure.api.api_client as api_client
        api_client._resilient_client = MagicMock()
        api_client._async_client = AsyncMock()
        api_client._async_client.is_closed = False

        with patch("src.infrastructure.api.api_client.close_async_client") as mock_close_async:
            with patch("asyncio.run"):
                close_client()

        assert api_client._resilient_client is None
        mock_close_async.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])