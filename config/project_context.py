"""
config/project_context.py — プロジェクト設定のシングルトンアクセサ

ProjectContext.get_setting(key, default) を用いて、
config/base.py に定義された定数や動的設定値に一元アクセスする。

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

from config.base import (
    BASE_DIR,
)
from config.models import GlobalConfigModel

logger = logging.getLogger(__name__)

# ==========================================
# グローバル設定オブジェクトとアクセサ
# ==========================================
_global_config: Optional[GlobalConfigModel] = None

def get_config() -> GlobalConfigModel:
    global _global_config
    if _global_config is None:
        # config/settings.py の ConfigManager を唯一のエントリポイントとして使用
        # (SSOT: settings.toml → Pydantic 検証 → 明示的環境変数マージ)
        try:
            from config.settings import ConfigManager
            _global_config = ConfigManager.get_config()
        except Exception as e:
            logger.critical(f"設定ファイルのバリデーションに失敗しました: {str(e)}")
            raise SystemExit("設定ファイルのバリデーションに失敗しました。アプリケーションを終了します。")
    return _global_config

def set_config(config: GlobalConfigModel) -> None:
    global _global_config
    _global_config = config


class ProjectContext:
    """
    プロジェクト全体の設定に型安全にアクセスするためのシングルトン風ユーティリティ。
    静的メソッドのみで構成し、インスタンス化不要。
    内部的には get_config() に委譲し、設定の一元管理を保証します。
    """

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        cfg = get_config()
        if hasattr(cfg, key):
            return getattr(cfg, key)
        if default is None:
            logger.debug(f"[ProjectContext] 未知の設定キー: '{key}'。None を返します。")
        return default

    @staticmethod
    def set_setting(key: str, value: Any) -> None:
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
        set_config(GlobalConfigModel.default())
        logger.debug("[ProjectContext] 全ランタイム上書きをリセットしました。")


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
        """設定値を更新し、TOMLへ反映する"""
        if key not in GlobalConfigModel.model_fields.keys():
            raise KeyError(f"Unknown config key: {key}")
        self.update(**{key: value})

    def update(self, **kwargs) -> None:
        """複数の設定値を一括更新し、TOMLファイルへ永続化する"""
        current_cfg_dict = get_config().model_dump()
        validated = GlobalConfigModel(**{**current_cfg_dict, **kwargs})

        # メモリ上のグローバル設定を更新
        set_config(validated)

        # TOMLファイルへ永続化 (SSOT)
        self._persist_to_toml(validated)

    def _persist_to_toml(self, config_model: GlobalConfigModel) -> None:
        """設定モデルを TOML ファイルに書き出す"""
        import tomli_w
        settings_path = BASE_DIR / "config" / "settings.toml"
        try:
            # Pydanticモデルを辞書に変換し、セクション分けして保存
            data = config_model.model_dump()

            # 簡易的に [general] セクションに全てまとめる
            toml_data = {"general": data}

            with open(settings_path, "wb") as f:
                tomli_w.dump(toml_data, f)
            logger.info(f"[GlobalConfig] 設定を永続化しました: {settings_path}")
        except Exception as e:
            logger.error(f"[GlobalConfig] TOML永続化失敗: {e}")

    def get_auto_concurrency(self) -> int:
        return min(8, (os.cpu_count() or 1) * 2)


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
    path = BASE_DIR / "prompts" / "templates" / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")

