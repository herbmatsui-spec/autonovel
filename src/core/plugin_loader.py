import importlib
import logging
import pathlib
import sys
from typing import Optional


class PluginLoader:
    @staticmethod
    def load_all_plugins() -> None:
        """plugins/ ディレクトリ下の .py ファイルを自動ロードする"""
        try:
            plugins_path = pathlib.Path(__file__).parents[2] / "plugins"

            if not plugins_path.exists():
                logging.warning(f"Plugins directory not found: {plugins_path}")
                return

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
