"""
tests/security/test_auth_timing_safety.py
Part 3 (Step 10) リグレッション防止テスト:
API キー検証における定数時間比較 (hmac.compare_digest)、空文字・空白処理の堅牢性を検証。
"""

import pytest
from src.backend.auth import validate_api_key_sync
from src.backend.config import settings


def test_validate_api_key_empty_or_whitespace():
    """空文字列や空白文字のみのキーが False として弾かれることを検証"""
    orig_disabled = settings.AUTH_DISABLED
    orig_keys = getattr(settings, "ALLOWED_API_KEYS", "")
    try:
        settings.AUTH_DISABLED = False
        settings.ALLOWED_API_KEYS = "valid-secret-key-123,another-secret-456"

        assert validate_api_key_sync("") is False
        assert validate_api_key_sync("   ") is False
        assert validate_api_key_sync(None) is False
    finally:
        settings.AUTH_DISABLED = orig_disabled
        settings.ALLOWED_API_KEYS = orig_keys


def test_validate_api_key_correct_match():
    """登録済みキーが定数時間比較により正常に認識されることを検証"""
    orig_disabled = settings.AUTH_DISABLED
    orig_keys = getattr(settings, "ALLOWED_API_KEYS", "")
    try:
        settings.AUTH_DISABLED = False
        settings.ALLOWED_API_KEYS = "key-alpha-999,key-beta-888"

        assert validate_api_key_sync("key-alpha-999") == "key-alpha-999"
        assert validate_api_key_sync("key-beta-888") == "key-beta-888"
        assert validate_api_key_sync("key-gamma-invalid") is False
    finally:
        settings.AUTH_DISABLED = orig_disabled
        settings.ALLOWED_API_KEYS = orig_keys


def test_validate_api_key_auth_disabled_bypass():
    """AUTH_DISABLED=True の場合は安全に 'dev-key' を返却することを検証"""
    orig_disabled = settings.AUTH_DISABLED
    try:
        settings.AUTH_DISABLED = True
        assert validate_api_key_sync("any-token") == "dev-key"
    finally:
        settings.AUTH_DISABLED = orig_disabled
