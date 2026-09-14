import pytest
from fastapi import HTTPException
from src.backend.config import Settings
from src.backend.security.jwt import create_access_token, create_refresh_token, decode_token


def test_production_fails_fast_with_default_or_missing_secret():
    """本番環境でJWT_SECRET_KEYが未設定またはデフォルトの場合に起動阻止例外を送出することを検証"""
    prod_settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="autonovel-super-secret-key-32bytes-minimum-change-in-prod",
    )
    with pytest.raises(ValueError, match="CRITICAL SECURITY RISK"):
        prod_settings.get_jwt_secret_key()

    prod_settings_empty = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="",
    )
    with pytest.raises(ValueError, match="CRITICAL SECURITY RISK"):
        prod_settings_empty.get_jwt_secret_key()

    prod_settings_short = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="short-key",
    )
    with pytest.raises(ValueError, match="CRITICAL SECURITY RISK"):
        prod_settings_short.get_jwt_secret_key()


def test_production_accepts_valid_strong_secret():
    """本番環境で十分な長さの安全な秘密鍵が設定されていれば正しく受理されることを検証"""
    strong_key = "a" * 32
    prod_settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY=strong_key,
    )
    assert prod_settings.get_jwt_secret_key() == strong_key


def test_jwt_token_generation_and_type_enforcement():
    """アクセストークンとリフレッシュトークンの発行および型検証"""
    token = create_access_token(user_id=42, role="user")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["role"] == "user"
    assert payload["type"] == "access"

    # リフレッシュトークンをアクセストークンとして復号しようとすると弾かれる
    refresh_token = create_refresh_token(user_id=42)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(refresh_token, expected_type="access")
    assert exc_info.value.status_code == 401
