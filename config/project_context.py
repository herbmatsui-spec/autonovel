"""
config/project_context.py — 後方互換シャム (非推奨)

このモジュールは非推奨です。新しいコードでは config.settings を直接使用してください。
"""

import warnings
from typing import Any

from config.settings import Settings, get_settings, reset_settings

# 非推奨警告
warnings.warn(
    "config.project_context は非推奨です。config.settings を直接使用してください。",
    DeprecationWarning,
    stacklevel=2,
)

# 後方互換用のエイリアス
Settings = Settings
get_settings = get_settings
reset_settings = reset_settings

GlobalConfigModel = Settings
GlobalConfig = Settings

PROMPT_TEMPLATES = {}


def get_config() -> Settings:
    """非推奨: get_settings() を使用してください。"""
    warnings.warn(
        "config.project_context.get_config() は非推奨です。config.settings.get_settings() を使用してください。",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_settings()


def set_config(config) -> None:
    """非推奨: 設定の変更は環境変数または .env ファイルで行ってください。"""
    warnings.warn(
        "config.project_context.set_config() は非推奨です。設定の変更は環境変数または .env ファイルで行ってください。",
        DeprecationWarning,
        stacklevel=2,
    )


class ProjectContext:
    """非推奨: config.settings.get_settings() を直接使用してください。"""

    def __init__(self):
        warnings.warn(
            "ProjectContext は非推奨です。config.settings.get_settings() を直接使用してください。",
            DeprecationWarning,
            stacklevel=2,
        )

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        warnings.warn(
            "ProjectContext.get_setting() は非推奨です。config.settings.get_settings().KEY を直接使用してください。",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(get_settings(), key, default)

    @staticmethod
    def set_setting(key: str, value: Any) -> None:
        warnings.warn(
            "ProjectContext.set_setting() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )

    @staticmethod
    def reset_overrides() -> None:
        warnings.warn(
            "ProjectContext.reset_overrides() は非推奨です。config.settings.reset_settings() を使用してください。",
            DeprecationWarning,
            stacklevel=2,
        )
        reset_settings()

    @staticmethod
    def validate_consistency():
        warnings.warn(
            "ProjectContext.validate_consistency() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )
        return get_settings().validate_consistency()


class GlobalConfig:
    """非推奨: config.settings.get_settings() を直接使用してください。"""

    def __init__(self):
        warnings.warn(
            "GlobalConfig は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )

    def get(self, key: str, default=None):
        warnings.warn(
            "GlobalConfig.get() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(get_settings(), key, default)

    def set(self, key: str, value) -> None:
        warnings.warn(
            "GlobalConfig.set() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )

    def update(self, **kwargs) -> None:
        warnings.warn(
            "GlobalConfig.update() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )

    def get_auto_concurrency(self) -> int:
        warnings.warn(
            "GlobalConfig.get_auto_concurrency() は非推奨です。",
            DeprecationWarning,
            stacklevel=2,
        )
        return get_settings().get_auto_concurrency()
