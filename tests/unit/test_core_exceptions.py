"""認証機能のテスト"""
import os

import pytest

# 環境変数を設定してからアプリをインポート
os.environ["ALLOWED_API_KEYS"] = "test-key-1,test-key-2"
os.environ["AUTH_DISABLED"] = "false"

from src.backend.auth import APIKeyService, validate_api_key_or_raise
from src.core.exceptions import AppError


def test_api_key_service_valid():
    """有効なAPIキーで検証が通ること"""
    service = APIKeyService(allowed_keys=["test-key-1", "test-key-2"], disabled=False)
    assert service.validate("test-key-1") is True
    assert service.validate("test-key-2") is True


def test_api_key_service_invalid():
    """無効なAPIキーで検証が失敗すること"""
    service = APIKeyService(allowed_keys=["test-key-1", "test-key-2"], disabled=False)
    assert service.validate("invalid-key") is False


def test_api_key_service_empty_allowed_keys():
    """allowed_keys が空の場合は False を返すこと（フェイルクローズ）"""
    service = APIKeyService(allowed_keys=[], disabled=False)
    assert service.validate("any-key") is False


def test_api_key_service_disabled():
    """disabled=True の場合は常に True を返すこと"""
    service = APIKeyService(allowed_keys=[], disabled=True)
    assert service.validate("any-key") is True


def test_validate_api_key_or_raise_valid():
    """有効なキーで例外が出ないこと"""
    os.environ["ALLOWED_API_KEYS"] = "test-key-1"
    os.environ["AUTH_DISABLED"] = "false"
    # キャッシュをクリア
    import src.backend.auth as auth_module
    auth_module._api_key_service = None

    result = validate_api_key_or_raise("test-key-1")
    assert result == "test-key-1"


def test_validate_api_key_or_raise_invalid():
    """無効なキーで AppError が発生すること"""
    os.environ["ALLOWED_API_KEYS"] = "test-key-1"
    os.environ["AUTH_DISABLED"] = "false"
    import src.backend.auth as auth_module
    auth_module._api_key_service = None

    with pytest.raises(AppError) as exc_info:
        validate_api_key_or_raise("invalid-key")
    assert exc_info.value.error_code == "FORBIDDEN"
    assert exc_info.value.status_code == 403


def test_validate_api_key_or_raise_empty_allowed():
    """allowed_keys が空の場合は AppError が発生すること"""
    os.environ["ALLOWED_API_KEYS"] = ""
    os.environ["AUTH_DISABLED"] = "false"
    import src.backend.auth as auth_module
    auth_module._api_key_service = None

    with pytest.raises(AppError) as exc_info:
        validate_api_key_or_raise("any-key")
    assert exc_info.value.error_code == "FORBIDDEN"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
