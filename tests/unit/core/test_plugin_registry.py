"""Step 18 検証テスト: プラグインレジストリ PluginRegistry の単体テスト."""

from __future__ import annotations

from unittest.mock import patch

from src.core.plugin_registry import (
    PluginRegistry,
    get_plugin_registry,
    reset_plugin_registry,
)


class TestPluginRegistryDiscovery:
    def test_all_plugins_disabled_by_default(self, monkeypatch):
        """ENABLE_* が未設定のとき、全プラグインが無効と判定されること。"""
        for flag in ("ENABLE_MULTIMEDIA", "ENABLE_AUDIO_SYNTH", "ENABLE_SOCIAL_POSTING"):
            monkeypatch.delenv(flag, raising=False)
        registry = PluginRegistry()
        assert registry.is_enabled("multimedia") is False
        assert registry.is_enabled("audio") is False
        assert registry.is_enabled("social_posting") is False

    def test_flag_enabled_by_env(self, monkeypatch):
        """ENABLE_MULTIMEDIA=true 時のみ multimedia が有効になること。"""
        monkeypatch.delenv("ENABLE_AUDIO_SYNTH", raising=False)
        monkeypatch.delenv("ENABLE_SOCIAL_POSTING", raising=False)
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        registry = PluginRegistry()
        assert registry.is_enabled("multimedia") is True
        assert registry.is_enabled("audio") is False

    def test_flag_accepts_various_truthy_values(self, monkeypatch):
        for value in ("1", "yes", "on", "TRUE"):
            monkeypatch.setenv("ENABLE_MULTIMEDIA", value)
            registry = PluginRegistry()
            assert registry.is_enabled("multimedia") is True

    def test_unknown_plugin_not_enabled(self, monkeypatch):
        monkeypatch.delenv("ENABLE_MULTIMEDIA", raising=False)
        registry = PluginRegistry()
        assert registry.is_enabled("nonexistent") is False

    def test_known_plugins_listed(self):
        registry = PluginRegistry()
        names = registry.known_plugins()
        assert "multimedia" in names
        assert "audio" in names


class TestPluginRegistryLoading:
    def test_load_disabled_plugin_returns_false(self, monkeypatch):
        """無効フラグのプラグインはロードしないこと。"""
        monkeypatch.delenv("ENABLE_MULTIMEDIA", raising=False)
        registry = PluginRegistry()
        assert registry.load("multimedia") is False
        assert registry.is_loaded("multimedia") is False

    def test_load_enabled_plugin(self, monkeypatch):
        """有効フラグのプラグインがロード・初期化されること。"""
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        registry = PluginRegistry()
        assert registry.load("multimedia") is True
        assert registry.is_loaded("multimedia") is True
        plugin = registry.get("multimedia")
        assert plugin is not None
        assert plugin.name == "multimedia"

    def test_load_unknown_plugin_returns_false(self):
        registry = PluginRegistry()
        assert registry.load("nonexistent") is False

    def test_get_or_load(self, monkeypatch):
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        registry = PluginRegistry()
        plugin = registry.get_or_load("multimedia")
        assert plugin is not None
        assert registry.is_loaded("multimedia") is True

    def test_load_all_only_enabled(self, monkeypatch):
        """load_all() は有効プラグインのみロードすること。"""
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        monkeypatch.delenv("ENABLE_AUDIO_SYNTH", raising=False)
        registry = PluginRegistry()
        results = registry.load_all()
        assert results == {"multimedia": True}


class TestPluginRegistryShutdown:
    def test_shutdown_all(self, monkeypatch):
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        registry = PluginRegistry()
        registry.load("multimedia")
        registry.shutdown_all()
        assert registry.is_loaded("multimedia") is False

    def test_disable(self, monkeypatch):
        monkeypatch.setenv("ENABLE_MULTIMEDIA", "true")
        registry = PluginRegistry()
        registry.load("multimedia")
        assert registry.disable("multimedia") is True
        assert registry.is_enabled("multimedia") is False
        assert registry.is_loaded("multimedia") is False

    def test_disable_unknown_returns_false(self):
        registry = PluginRegistry()
        assert registry.disable("nonexistent") is False


class TestModuleLevelRegistry:
    def test_get_plugin_registry_lazy(self):
        reset_plugin_registry()
        registry = get_plugin_registry()
        assert registry is not None
        assert registry is get_plugin_registry()

    def test_reset_plugin_registry(self):
        reset_plugin_registry()
        first = get_plugin_registry()
        reset_plugin_registry()
        second = get_plugin_registry()
        assert first is not second
