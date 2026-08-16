"""
config/project_context.py — プロジェクト設定のシングルトンアクセサ (新統一設定版)

ProjectContext.get_setting(key, default) を用いて、
統一設定クラス (config.settings.Settings) に定義された設定値に一元アクセスする。

使用例:
    from config.project_context import ProjectContext
    model = ProjectContext.get_setting("model_writing")
    is_fast = ProjectContext.get_setting("fail_fast_mode", False)

注意:
    このモジュールは Streamlit に依存しません。
    Streamlit UI との連携が必要な場合は config.streamlit_adapter を使用してください。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# ==========================================
# グローバル設定オブジェクトとアクセサ
# ==========================================
_settings_instance: Optional[Settings] = None


def get_config() -> Settings:
    """統一設定インスタンスを取得"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = get_settings()
    return _settings_instance


def set_config(config: Settings) -> None:
    global _settings_instance
    _settings_instance = config


class ProjectContext:
    """
    プロジェクト全体の設定に型安全にアクセスするためのシングルトン風ユーティリティ。
    静的メソッドのみで構成し、インスタンス化不要。
    内部的には統一設定クラス (Settings) に委譲し、設定の一元管理を保証します。
    """

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """設定値を取得（型安全・デフォルト値対応）"""
        cfg = get_config()
        if hasattr(cfg, key):
            return getattr(cfg, key)
        if default is None:
            logger.debug(f"[ProjectContext] 未知の設定キー: '{key}'。None を返します。")
        return default

    @staticmethod
    def set_setting(key: str, value: Any) -> None:
        """設定値を上書き（ランタイムのみ、永続化はしない）"""
        cfg = get_config()
        if hasattr(cfg, key):
            setattr(cfg, key, value)
            set_config(cfg)
            logger.info(f"[ProjectContext] 設定を上書きしました: {key} = {value!r}")
        else:
            logger.warning(f"[ProjectContext] Unknown config key: {key}")

    @staticmethod
    def reset_overrides() -> None:
        """テストや動的オーバーライドをリセットし、デフォルト値に戻す。"""
        from config.settings import reset_settings
        reset_settings()
        logger.debug("[ProjectContext] 全ランタイム上書きをリセットしました。")

    @staticmethod
    def validate_consistency() -> list[str]:
        """設定の整合性を検証"""
        return get_config().validate_consistency()


class GlobalConfig:
    """
    アプリケーション全体の設定を管理する基底クラス。
    Streamlit に依存しない純粋な設定アクセスを提供する。
    Streamlit 連携が必要な場合は config.streamlit_adapter.StreamlitConfig を使用。
    """

    def __init__(self):
        pass

    def get(self, key: str, default=None):
        """設定値を取得する"""
        return getattr(get_config(), key, default)

    def set(self, key: str, value) -> None:
        """設定値を更新する（ランタイムのみ）"""
        cfg = get_config()
        if not hasattr(cfg, key):
            raise KeyError(f"Unknown config key: {key}")
        setattr(cfg, key, value)
        logger.info(f"[GlobalConfig] 設定を更新: {key} = {value!r}")

    def update(self, **kwargs) -> None:
        """複数の設定値を一括更新する（ランタイムのみ、永続化は別途必要）"""
        cfg = get_config()
        for key, value in kwargs.items():
            if not hasattr(cfg, key):
                raise KeyError(f"Unknown config key: {key}")
            setattr(cfg, key, value)
        logger.info(f"[GlobalConfig] 設定を一括更新: {list(kwargs.keys())}")

    def get_auto_concurrency(self) -> int:
        return get_config().get_auto_concurrency()


# ==========================================
# 後方互換エイリアス
# ==========================================

# 旧 GlobalConfigModel のデフォルトインスタンス生成用
def _get_default_global_config():
    """後方互換: GlobalConfigModel.default() 相当"""
    return get_config()


# 旧 get_config() 関数の互換ラッパー（GlobalConfigModel 返却を期待するコード用）
def _get_global_config_model():
    """
    後方互換ラッパー: 旧 GlobalConfigModel インターフェースを期待するコード用。
    実際の Settings インスタンスを返すが、Pydantic モデルとして振る舞う。
    """
    return get_config()


# ==========================================
# Jinja2 プロンプトテンプレート定義
# ==========================================
PROMPT_TEMPLATES: Dict[str, str] = {
    "style_instruction.j2": """
【Target Style: {{ style_name }}】
【Dialogue Ratio】: {{ dialogue_ratio }}
{{ instruction }}
{{ dna_correction }}
""",
}


def get_prompt_template(name: str) -> str:
    from config.settings import BASE_DIR
    path = BASE_DIR / "prompts" / "templates" / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


# ==========================================
# 後方互換用: 旧モジュールからのインポートを維持
# ==========================================
try:
    from config.constants import BASE_DIR as _BASE_DIR
except ImportError:
    from config.settings import BASE_DIR as _BASE_DIR

BASE_DIR = _BASE_DIR

# 旧 GlobalConfigModel への参照を期待するコードのための型エイリアス
from config.settings import Settings as GlobalConfigModel