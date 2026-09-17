from __future__ import annotations

import pytest
from unittest.mock import mock_open, patch

from src.core.system_plugin_loader import SystemPluginLoader


@pytest.fixture(autouse=True)
def reset_loader_state():
    # 各テスト前後にキャッシュと設定をクリア
    SystemPluginLoader._config = None
    SystemPluginLoader._class_cache = {}
    yield
    SystemPluginLoader._config = None
    SystemPluginLoader._class_cache = {}


def test_load_config_file_not_found():
    with patch("os.path.exists", return_value=False):
        config = SystemPluginLoader._load_config()
        assert config == {}


def test_load_config_yaml_error():
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="invalid: yaml: :")):
            config = SystemPluginLoader._load_config()
            assert config == {}


def test_load_config_success():
    yaml_content = """
    plugins:
      test_plugin:
        module: math
        class: hypot
    """
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = SystemPluginLoader._load_config()
            assert "test_plugin" in config
            assert config["test_plugin"]["module"] == "math"


def test_get_plugin_class_cached():
    SystemPluginLoader._class_cache["cached_plugin"] = int
    result = SystemPluginLoader.get_plugin_class("cached_plugin")
    assert result is int


def test_get_plugin_class_not_defined():
    SystemPluginLoader._config = {}
    result = SystemPluginLoader.get_plugin_class("unknown", default_class=str)
    assert result is str


def test_get_plugin_class_invalid_config():
    SystemPluginLoader._config = {
        "bad_plugin": {"module": "math"}  # missing class
    }
    result = SystemPluginLoader.get_plugin_class("bad_plugin", default_class=float)
    assert result is float


def test_get_plugin_class_import_error():
    SystemPluginLoader._config = {
        "no_module": {"module": "non_existent_module_xyz", "class": "SomeClass"}
    }
    result = SystemPluginLoader.get_plugin_class("no_module", default_class=dict)
    assert result is dict


def test_get_plugin_class_attribute_error():
    SystemPluginLoader._config = {
        "no_attr": {"module": "math", "class": "NonExistentFunctionInMath"}
    }
    result = SystemPluginLoader.get_plugin_class("no_attr", default_class=list)
    assert result is list


def test_get_plugin_class_success():
    SystemPluginLoader._config = {
        "valid_plugin": {"module": "unittest.mock", "class": "MagicMock"}
    }
    from unittest.mock import MagicMock
    result = SystemPluginLoader.get_plugin_class("valid_plugin")
    assert result is MagicMock
    assert SystemPluginLoader._class_cache["valid_plugin"] is MagicMock
