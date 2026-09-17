"""config.py の本番環境バリデーション検証テスト"""
import pytest
from pydantic import ValidationError


def test_production_rejects_auth_disabled():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="AUTH_DISABLED"):
        Settings(
            APP_ENV="production",
            AUTH_DISABLED=True,
            JWT_SECRET_KEY="a" * 64,
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
        )


def test_production_rejects_weak_jwt():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="change-in-prod",
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
        )


def test_production_rejects_sqlite():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 64,
            DATABASE_URL="sqlite:///test.db",
        )


def test_development_allows_defaults():
    from src.backend.config import Settings
    s = Settings(APP_ENV="development")
    assert s.APP_ENV == "development"
