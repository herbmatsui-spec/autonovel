import importlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type

import yaml

logger = logging.getLogger(__name__)

class SystemPluginLoader:
    """
    動的にシステムプラグイン（オプショナルなモジュール/クラス）をロードするためのローダー。
    config/system_plugins.yaml で設定された module と class に基づき、
    ハードコードされた import なしで動的ロードを実現する。
    """

    _config: Optional[Dict[str, Any]] = None
    _class_cache: Dict[str, Type] = {}
    _config_path = os.path.join(Path(__file__).parent.parent.parent, "config", "system_plugins.yaml")

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        if cls._config is not None:
            return cls._config

        if not os.path.exists(cls._config_path):
            logger.warning(f"Plugin config file not found: {cls._config_path}")
            cls._config = {}
            return cls._config

        try:
            with open(cls._config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cls._config = data.get("plugins", {}) if data else {}
        except Exception as e:
            logger.error(f"Failed to load system_plugins.yaml: {e}")
            cls._config = {}

        return cls._config

    @classmethod
    def get_plugin_class(cls, plugin_name: str, default_class: Optional[Type] = None) -> Optional[Type]:
        """
        指定されたプラグイン名に対応するクラスを動的にロードして返す。
        ロードに失敗した場合や設定が存在しない場合は、default_class を返す。
        """
        if plugin_name in cls._class_cache:
            return cls._class_cache[plugin_name]

        config = cls._load_config()
        if plugin_name not in config:
            logger.debug(f"Plugin '{plugin_name}' is not defined in system_plugins.yaml. Using default.")
            return default_class

        plugin_info = config[plugin_name]
        module_path = plugin_info.get("module")
        class_name = plugin_info.get("class")

        if not module_path or not class_name:
            logger.error(f"Invalid plugin configuration for '{plugin_name}': {plugin_info}")
            return default_class

        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            cls._class_cache[plugin_name] = plugin_class
            logger.info(f"Successfully loaded plugin class: {module_path}.{class_name}")
            return plugin_class
        except ImportError as e:
            logger.error(f"Failed to import module '{module_path}' for plugin '{plugin_name}': {e}")
        except AttributeError as e:
            logger.error(f"Class '{class_name}' not found in module '{module_path}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading plugin '{plugin_name}': {e}")

        return default_class
