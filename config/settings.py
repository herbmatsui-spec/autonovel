"""
config/settings.py — 設定統一プロキシレイヤー (非推奨互換モジュール)

.. deprecated:: 4.9.4
    設定は `src.backend.config.settings` を SSOT (Single Source of Truth) として
    一元管理されています。新規コードでは `from src.backend.config import settings` を
    使用してください。
"""

from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from typing import Any

from schemas.config import GlobalConfigModel
from src.backend.config import settings as backend_settings

logger = logging.getLogger(__name__)

# 旧属性名と新属性名のマッピング
_ATTRIBUTE_ALIASES: dict[str, str] = {
    "cors_allowed_origins": "CORS_ORIGINS",
    "database_url": "DATABASE_URL",
    "api_host": "HOST",
    "api_port": "PORT",
    "log_level": "LOG_LEVEL",
}


class ConfigManager:
    _instance: GlobalConfigModel | None = None

    @classmethod
    def get_config(cls) -> GlobalConfigModel:
        if cls._instance is None:
            cls._instance = GlobalConfigModel.load()
        return cls._instance


class SettingsProxy:
    """
    旧 config.settings へのアクセスを src.backend.config.settings へ委譲する互換プロキシ。
    小文字プロパティと大文字プロパティの双方を透過的に解決する。
    """

    def __init__(self) -> None:
        object.__setattr__(self, "_overrides", {})

    def __getattr__(self, name: str) -> Any:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            return overrides[name]

        # エイリアスマッピング
        target_name = _ATTRIBUTE_ALIASES.get(name, name)

        if hasattr(backend_settings, target_name):
            return getattr(backend_settings, target_name)
        if hasattr(backend_settings, target_name.upper()):
            return getattr(backend_settings, target_name.upper())
        if hasattr(backend_settings, target_name.lower()):
            return getattr(backend_settings, target_name.lower())

        raise AttributeError(f"'Settings' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_overrides":
            object.__setattr__(self, name, value)
            return

        overrides = object.__getattribute__(self, "_overrides")
        overrides[name] = value

        # backend_settings 側にも可能な限り反映
        target_name = _ATTRIBUTE_ALIASES.get(name, name)
        if hasattr(backend_settings, target_name):
            try:
                setattr(backend_settings, target_name, value)
            except Exception:
                pass
        elif hasattr(backend_settings, target_name.upper()):
            try:
                setattr(backend_settings, target_name.upper(), value)
            except Exception:
                pass


# シングルトンインスタンス
settings = SettingsProxy()


# クラスとしての参照互換 (Settings() の呼び出しに対応)
class Settings(SettingsProxy):
    def __new__(cls, *args: Any, **kwargs: Any) -> SettingsProxy:
        return settings


@lru_cache()
def get_settings() -> SettingsProxy:
    return settings