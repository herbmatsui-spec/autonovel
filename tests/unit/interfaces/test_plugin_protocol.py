"""Step 15 検証テスト: PluginProtocol の単体テスト。"""

from __future__ import annotations

from src.interfaces.plugin import BasePlugin, PluginProtocol


class DummyPlugin(BasePlugin):
    name = "dummy"

    def initialize(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass


class TestPluginProtocol:
    def test_dummy_plugin_satisfies_protocol(self):
        """BasePlugin 派生クラスは PluginProtocol を満たす。"""
        plugin = DummyPlugin()
        assert isinstance(plugin, PluginProtocol)

    def test_protocol_defines_required_methods(self):
        """プロトコルが initialize / is_available / shutdown を定義すること。"""
        for method in ("initialize", "is_available", "shutdown"):
            assert hasattr(PluginProtocol, method), f"missing method: {method}"

    def test_base_plugin_default_initialize(self):
        plugin = BasePlugin()
        assert plugin.initialize() is True
        assert plugin.is_available() is True

    def test_base_plugin_default_shutdown(self):
        plugin = BasePlugin()
        plugin.initialize()
        plugin.shutdown()
        assert plugin.is_available() is False

    def test_base_plugin_stores_config(self):
        plugin = BasePlugin(api_key="x", region="jp")
        assert plugin.config == {"api_key": "x", "region": "jp"}

    def test_base_plugin_default_name(self):
        plugin = BasePlugin()
        assert plugin.name == "base"

    def test_subclass_name_override(self):
        plugin = DummyPlugin()
        assert plugin.name == "dummy"
