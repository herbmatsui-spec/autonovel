from schemas.config import GlobalConfigModel
from pydantic_settings import BaseSettings
from functools import lru_cache


class ConfigManager:
    _instance: GlobalConfigModel = None

    @classmethod
    def get_config(cls) -> GlobalConfigModel:
        if cls._instance is None:
            cls._instance = GlobalConfigModel.load()
        return cls._instance


class Settings(BaseSettings):
    # CORS: raw environment string (comma-separated or JSON array).
    # Parsing into a list is handled in config/cors_config.py so that both
    # formats are accepted (pydantic-settings v2 only accepts JSON for lists).
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:8501"
    # Database
    database_url: str = "sqlite:///./autonovel.db"
    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Backwards-compatible module-level singleton
settings = Settings()
