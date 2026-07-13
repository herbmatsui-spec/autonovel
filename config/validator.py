from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from schemas.config import (
    DomainProfileModel,
    GlobalConfigModel,
    InteractionMatrixModel,
    ModelRegistryModel,
    SystemPluginsModel,
    TropesModel,
)

logger = logging.getLogger(__name__)


class ConfigValidator:
    @staticmethod
    def load_settings_toml(path: str = "config/settings.toml") -> GlobalConfigModel:
        logger.debug(f"[LOAD] ConfigValidator.load_settings_toml() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")
            with open(path, "rb") as f:
                import tomllib
                data = tomllib.load(f)
            # [general] セクションを正しく抽出
            flat_data = data.get("general", {})
            logger.debug(f"[LOAD] settings.toml loaded: {len(flat_data)} keys")
            model = GlobalConfigModel(**flat_data)
            # SSOT に対する明示的環境変数上書きを適用
            return GlobalConfigModel.apply_env_overrides(model)
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def load_models_yaml(path: str = "config/models.yaml") -> ModelRegistryModel:
        logger.debug(f"[LOAD] ConfigValidator.load_models_yaml() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            result = ModelRegistryModel(**data["model_registry"]) if "model_registry" in data else ModelRegistryModel()
            logger.debug(f"[LOAD] models.yaml loaded: planning={result.planning}")
            return result
        except Exception as e:
            logger.error(f"models.yaml の読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def load_system_plugins_yaml(path: str = "config/system_plugins.yaml") -> SystemPluginsModel:
        logger.debug(f"[LOAD] ConfigValidator.load_system_plugins_yaml() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            result = SystemPluginsModel(**data["plugins"]) if "plugins" in data else SystemPluginsModel()
            logger.debug("[LOAD] system_plugins.yaml loaded")
            return result
        except Exception as e:
            logger.error(f"system_plugins.yaml の読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def load_tropes_json(path: str = "config/tropes.json") -> TropesModel:
        logger.debug(f"[LOAD] ConfigValidator.load_tropes_json() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = TropesModel(**data)
            logger.debug(f"[LOAD] tropes.json loaded: {len(result.tropes)} tropes")
            return result
        except Exception as e:
            # If JSON decode error, delete the invalid file to allow test cleanup
            if isinstance(e, json.JSONDecodeError):
                try:
                    Path(path).unlink(missing_ok=True)
                    logger.debug("Deleted invalid tropes.json after JSONDecodeError")
                except Exception as del_e:
                    logger.warning(f"Failed to delete invalid tropes.json: {del_e}")
            logger.error(f"tropes.json の読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def load_interaction_matrix_yaml(path: str = "config/interaction_matrix.yaml") -> InteractionMatrixModel:
        logger.debug(f"[LOAD] ConfigValidator.load_interaction_matrix_yaml() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            result = InteractionMatrixModel(**data)
            logger.debug("[LOAD] interaction_matrix.yaml loaded")
            return result
        except Exception as e:
            logger.error(f"interaction_matrix.yaml の読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def load_domain_profile_json(path: str) -> DomainProfileModel:
        logger.debug(f"[LOAD] ConfigValidator.load_domain_profile_json() called from: path={path}")
        try:
            if not Path(path).exists():
                raise FileNotFoundError(f"ドメインプロファイルが見つかりません: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = DomainProfileModel(**data)
            logger.debug(f"[LOAD] domain_profile loaded: {Path(path).stem}")
            return result
        except Exception as e:
            logger.error(f"ドメインプロファイルの読み込みに失敗しました: {str(e)}")
            raise

    @staticmethod
    def validate_all(strict: bool = True) -> Dict[str, Any]:
        """
        全設定ファイルをバリデーションし、成功した場合は辞書形式で返す。
        `settings` キーには全設定がマージされた GlobalConfigModel が格納される。
        
        Args:
            strict: True（デフォルト）→ 1ファイルでも失敗したら例外を投げる
                    False → 失敗したファイルはデフォルト値で代替し、可能な限り続行
        
        Returns:
            各設定ファイルのパース結果を含む辞書。
            失敗した項目はデフォルト値のインスタンスで埋められる（strict=False時）。
        """
        logger.debug("[LOAD] ===== ConfigValidator.validate_all() called ====")
        import traceback
        logger.debug(f"[LOAD] Call stack: {''.join(traceback.format_stack()[:-1])}")

        # 安全ロードヘルパー: strict=False 時に例外をデフォルト値で代替
        def _safe_load(loader_func, default_factory, label: str):
            try:
                return loader_func()
            except Exception as e:
                logger.warning(f"{label} の読み込みに失敗（strict=False: デフォルト値で代替）: {e}")
                if strict:
                    raise
                return default_factory()

        # 1. 個別ファイルをロード
        settings_model = _safe_load(
            ConfigValidator.load_settings_toml,
            lambda: GlobalConfigModel(),
            "settings.toml"
        )
        models = _safe_load(
            ConfigValidator.load_models_yaml,
            lambda: ModelRegistryModel(),
            "models.yaml"
        )
        plugins = _safe_load(
            ConfigValidator.load_system_plugins_yaml,
            lambda: SystemPluginsModel(),
            "system_plugins.yaml"
        )
        tropes = _safe_load(
            ConfigValidator.load_tropes_json,
            lambda: TropesModel(),
            "tropes.json"
        )
        interaction = _safe_load(
            ConfigValidator.load_interaction_matrix_yaml,
            lambda: InteractionMatrixModel(),
            "interaction_matrix.yaml"
        )

        # 2. ドメインプロファイルの読み込み
        domain_profiles = {}
        domain_dir = Path("config/domain_profiles")
        if domain_dir.exists():
            for file in domain_dir.glob("*.json"):
                try:
                    domain_profiles[file.stem] = ConfigValidator.load_domain_profile_json(str(file))
                except Exception as e:
                    logger.warning(f"{file.name} の読み込みに失敗: {e}")
                    if strict:
                        raise

        # 3. models.yaml の値を settings にマージ（TOMLにないキーのみ上書き）
        merged_dict = settings_model.model_dump()
        model_key_map = {
            "planning": "model_planning",
            "plot_expansion": "model_plot_expansion",
            "writing": "model_writing",
            "climax": "model_climax",
            "fallback": "model_stable_fallback",
            "ultra_stable": "model_ultra_stable",
        }
        for yaml_key, model_key in model_key_map.items():
            if model_key not in merged_dict or merged_dict[model_key] == GlobalConfigModel.model_fields[model_key].default:
                val = getattr(models, yaml_key, None)
                if val:
                    merged_dict[model_key] = val

        # 4. 拡張設定をマージ
        merged_dict["domain_profiles"] = domain_profiles
        merged_dict["interaction_matrix"] = interaction.model_dump()
        merged_dict["tropes"] = tropes.model_dump()
        merged_dict["system_plugins"] = plugins.model_dump()

        # 5. マージ済み GlobalConfigModel を生成
        merged_settings = GlobalConfigModel(**merged_dict)

        # 6. SSOT に対する明示的環境変数上書きを適用 (models.yaml 統合後)
        merged_settings = GlobalConfigModel.apply_env_overrides(merged_settings)

        # 7. 論理整合性検証 (非致命: 警告ログのみ)
        consistency_errors = merged_settings.validate_consistency()
        for err in consistency_errors:
            logger.warning(f"[CONFIG] 設定整合性警告: {err}")
            if strict:
                raise ValueError(f"設定整合性エラー: {err}")

        logger.debug(f"[LOAD] ===== ConfigValidator.validate_all() completed: {len(domain_profiles)} domain profiles ====")

        return {
            "settings": merged_settings,
            "models": models,
            "plugins": plugins,
            "tropes": tropes,
            "interaction": interaction,
            "domain_profiles": domain_profiles
        }

