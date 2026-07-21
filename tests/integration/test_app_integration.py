import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.mocks.mock_streamlit import MockStreamlitContext, patch_streamlit


@pytest.fixture
def mock_st_context():
    """Streamlit コンテキストのモックを提供するフィクスチャ"""
    ctx = MockStreamlitContext()
    patch_streamlit(ctx)
    return ctx


@pytest.fixture
def mock_requests_get():
    """Mock requests.get to simulate backend health status."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "database": "ok", "worker": "ok"}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.mark.asyncio
async def test_app_main_easy_mode_success(mock_st_context, mock_requests_get, monkeypatch):
    """ケースA: 正常系 - 簡易モード。APIキーおよびバックエンドが正常。"""
    import streamlit_app.app as app
    from streamlit_app.state import UIStateStore

    async_validate_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("streamlit_app.health_check.validate_api_key_async", async_validate_mock)

    monkeypatch.setattr(app, "render_sidebar", lambda: "valid-api-key")

    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)

    engine_service_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.engine_service.EngineService.get_instance", lambda api_key=None: engine_service_mock)

    UIStateStore.get_runtime().app_mode = "easy"

    app.main()

    assert mock_st_context.navigation_run_called is True
    landing_mock.assert_not_called()


@pytest.mark.asyncio
async def test_app_main_advanced_mode_success(mock_st_context, mock_requests_get, monkeypatch):
    """ケースB: 正常系 - 詳細モード。APIキーおよびバックエンドが正常。"""
    import streamlit_app.app as app
    from streamlit_app.state import UIStateStore

    async_validate_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("streamlit_app.health_check.validate_api_key_async", async_validate_mock)

    monkeypatch.setattr(app, "render_sidebar", lambda: "valid-api-key")

    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)

    engine_service_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.engine_service.EngineService.get_instance", lambda api_key=None: engine_service_mock)

    UIStateStore.get_runtime().app_mode = "advanced"

    app.main()

    assert mock_st_context.navigation_run_called is True
    landing_mock.assert_not_called()


@pytest.mark.asyncio
async def test_app_main_backend_error(mock_st_context, mock_requests_get, monkeypatch):
    """ケースC: 異常系 - バックエンド未接続。自動起動UIの表示を確認。"""
    import streamlit_app.app as app

    mock_requests_get.side_effect = Exception("Connection refused")

    title_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.ui_utils.render_centered_title", title_mock)

    launcher_mock = MagicMock(return_value=True)
    monkeypatch.setattr("streamlit_app.backend_launcher.start_backend", launcher_mock)

    mock_st_context.click_button("🔄 バックエンドを自動起動する")

    app.main()

    title_mock.assert_called_once_with(
        "⚠️ システムステータス（バックエンド未接続）",
        "APIサーバーとの通信が確立されていません。以下の状態を確認・復旧してください。"
    )
    launcher_mock.assert_called_once()
    assert mock_st_context.rerun_called is True
    assert mock_st_context.navigation_run_called is False


@pytest.mark.asyncio
async def test_app_main_missing_or_invalid_api_key(mock_st_context, mock_requests_get, monkeypatch):
    """ケースD: 異常系 - APIキー無効/空。ランディング画面が表示される。"""
    import streamlit_app.app as app

    monkeypatch.setattr(app, "render_sidebar", lambda: None)

    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)

    app.main()

    landing_mock.assert_called_once()
    assert mock_st_context.navigation_run_called is False
