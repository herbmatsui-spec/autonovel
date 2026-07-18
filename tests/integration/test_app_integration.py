import pytest
from unittest.mock import AsyncMock, MagicMock

import pytest

from streamlit_app.app import app
from streamlit_app.state import UIStateStore


@pytest.fixture
def mock_st_context():
    """Streamlit コンテキストのモックを提供するフィクスチャ"""
    from tests.mocks.mock_streamlit import mock_st_context
    return mock_st_context()


@pytest.fixture
def mock_requests_get():
    """Mock requests.get to simulate backend health status."""
    from unittest.mock import MagicMock
    with patch("requests.get") as mock_get:
        # Default behavior: backend is healthy
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "database": "ok", "worker": "ok"}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.mark.asyncio
async def test_app_main_easy_mode_success(mock_st_context, mock_requests_get, monkeypatch):
    """ケースA: 正常系 - 簡易モード。APIキーおよびバックエンドが正常。"""
    # Import app inside the test
    import streamlit_app.app as app
    from streamlit_app.state import UIStateStore
    
    # 1. Mock API key validation to return True (async method)
    async_validate_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("streamlit_app.health_check.validate_api_key_async", async_validate_mock)
    
    # 2. Mock sidebar and landing in the app module context (due to "from module import function")
    monkeypatch.setattr(app, "render_sidebar", lambda: "valid-api-key")
    
    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)
    
    # 3. Mock EngineService
    engine_service_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.engine_service.EngineService.get_instance", lambda api_key=None: engine_service_mock)
    
    # Set mode to 'easy'
    UIStateStore.get_runtime().app_mode = "easy"
    
    # Run main()
    app.main()
    
    # Assert navigation was run
    assert mock_st_context.navigation_run_called is True
    landing_mock.assert_not_called()


@pytest.mark.asyncio
async def test_app_main_advanced_mode_success(mock_st_context, mock_requests_get, monkeypatch):
    """ケースB: 正常系 - 詳細モード。APIキーおよびバックエンドが正常。"""
    import streamlit_app.app as app
    from streamlit_app.state import UIStateStore
    
    # 1. Mock API key validation
    async_validate_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("streamlit_app.health_check.validate_api_key_async", async_validate_mock)
    
    # 2. Mock sidebar and landing
    monkeypatch.setattr(app, "render_sidebar", lambda: "valid-api-key")
    
    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)
    
    # 3. Mock EngineService
    engine_service_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.engine_service.EngineService.get_instance", lambda api_key=None: engine_service_mock)
    
    # Set mode to 'advanced'
    UIStateStore.get_runtime().app_mode = "advanced"
    
    # Run main()
    app.main()
    
    # Assert navigation was run
    assert mock_st_context.navigation_run_called is True
    landing_mock.assert_not_called()


@pytest.mark.asyncio
async def test_app_main_backend_error(mock_st_context, mock_requests_get, monkeypatch):
    """ケースC: 異常系 - バックエンド未接続。自動起動UIの表示を確認。"""
    import streamlit_app.app as app
    
    # 1. Configure requests.get mock to return connection error/failure
    mock_requests_get.side_effect = Exception("Connection refused")
    
    # 5. Mock UI utils (centered title) used in health check
    title_mock = MagicMock()
    monkeypatch.setattr("streamlit_app.ui_utils.render_centered_title", title_mock)
    
    # 5. Mock launcher to succeed when button clicked
    launcher_mock = MagicMock(return_value=True)
    monkeypatch.setattr("streamlit_app.backend_launcher.start_backend_processes", launcher_mock)
    
    # 3. Simulating button click in Streamlit (we clicked "🔄 バックエンドを自動起動する")
    mock_st_context.click_button("🔄 バックエンドを自動起動する")
    
    # Run main()
    app.main()
    
    # Assertions
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
    
    # 1. Mock sidebar to return None (no api key entered yet)
    monkeypatch.setattr(app, "render_sidebar", lambda: None)
    
    # 3. Mock landing page rendering (should be rendered since key is missing)
    landing_mock = MagicMock()
    monkeypatch.setattr(app, "render_landing", landing_mock)
    
    # Run main()
    app.main()
    
    # Assert landing page was shown and navigation was not run
    landing_mock.assert_called_once()
    assert mock_st_context.navigation_run_called is False