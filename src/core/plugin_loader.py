import importlib
import logging
import pathlib
import sys
from typing import Optional


class PluginLoader:
    _instance: Optional['PluginLoader'] = None

    @staticmethod
    def get_instance() -> 'PluginLoader':
        if PluginLoader._instance is None:
            PluginLoader._instance = PluginLoader()
        return PluginLoader._instance

    def load_all_plugins(self) -> None:
        """plugins/ ディレクトリ下の .py ファイルを自動ロードする"""
        try:
            # pluginsディレクトリのパスを特定
            # /src/core/plugin_loader.py から見て ../../plugins
            plugins_path = pathlib.Path(__file__).parents[2] / "plugins"

            if not plugins_path.exists():
                logging.warning(f"Plugins directory not found: {plugins_path}")
                return

            # パスを sys.path に追加してインポート可能にする
            if str(plugins_path.parent) not in sys.path:
                sys.path.insert(0, str(plugins_path.parent))

            for file in plugins_path.glob("*.py"):
                if file.name.startswith("_") or file.name == "__init__.py":
                    continue

                module_name = f"plugins.{file.stem}"
                try:
                    importlib.import_module(module_name)
                    logging.info(f"Successfully loaded plugin: {module_name}")
                except Exception as e:
                    logging.error(f"Failed to load plugin {module_name}: {e}")
        except Exception as e:
            logging.error(f"Error in load_all_plugins: {e}")
