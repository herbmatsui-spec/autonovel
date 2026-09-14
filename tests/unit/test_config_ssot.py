import pytest
from src.backend.config import Settings

def test_settings_default_values():
    settings = Settings(_env_file=None)
    assert settings.APP_NAME == "AutoNovel"
    assert settings.PORT == 8200
    assert settings.JWT_ALGORITHM == "HS256"

def test_settings_production_validation_rejects_missing_jwt():
    # 本番環境でJWTキーがない場合はエラー
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY=None,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
            _env_file=None,
        )

def test_settings_production_validation_rejects_sqlite():
    # 本番環境でSQLiteが指定されている場合はエラー
    with pytest.raises(ValueError, match="SQLite"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="secure-prod-key-minimum-32-chars-long",
            DATABASE_URL="sqlite:///test.db",
            _env_file=None,
        )