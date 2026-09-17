"""API Key が admin 権限を付与しないことを検証するテスト"""
import pytest
from unittest.mock import AsyncMock, patch
from src.backend.auth import require_admin_user_or_key, _get_dev_mock_user


@pytest.mark.asyncio
async def test_api_key_does_not_grant_admin():
    """API Key 認証が admin ロールを返さないことを確認"""
    with patch("src.backend.auth.settings") as mock_settings:
        mock_settings.AUTH_DISABLED = False
        mock_settings.ALLOWED_API_KEYS = ""
        with patch("src.backend.auth.require_api_key", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = "valid-key"
            with patch("src.backend.auth.decode_token", return_value=None):
                user = await require_admin_user_or_key(
                    token=None, authorization="Bearer valid-key", db=AsyncMock()
                )
                assert user.role != "admin", "API Key should not grant admin role"


def test_dev_mock_user_has_admin_role():
    """開発用モックユーザーは admin ロールを持つ（AUTH_DISABLED時のみ使用）"""
    user = _get_dev_mock_user()
    assert user.role == "admin"
