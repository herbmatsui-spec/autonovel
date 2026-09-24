"""Step 17 検証テスト: MultimediaService のプラグインカプセル化."""

from __future__ import annotations

from src.interfaces.plugin import PluginProtocol
from src.plugins.multimedia.plugin import MultimediaPlugin


class TestMultimediaPlugin:
    def test_satisfies_plugin_protocol(self):
        """MultimediaPlugin は PluginProtocol を満たす。"""
        plugin = MultimediaPlugin()
        assert isinstance(plugin, PluginProtocol)

    def test_initialize_imports_service(self):
        """initialize() が MultimediaService を束ねて成功すること。"""
        plugin = MultimediaPlugin()
        assert plugin.initialize() is True
        assert plugin.is_available() is True

    def test_get_service_class(self):
        plugin = MultimediaPlugin()
        plugin.initialize()
        service_cls = plugin.get_service_class()
        assert service_cls is not None
        assert service_cls.__name__ == "MultimediaService"

    def test_get_service_class_before_init(self):
        plugin = MultimediaPlugin()
        assert plugin.get_service_class() is None

    def test_shutdown_releases_service(self):
        plugin = MultimediaPlugin()
        plugin.initialize()
        plugin.shutdown()
        assert plugin.is_available() is False
        assert plugin.get_service_class() is None

    def test_plugin_name(self):
        assert MultimediaPlugin.name == "multimedia"
