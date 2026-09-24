"""Step 21 検証テスト: プラグイン完全無効化時のコアドメイン単体テスト.

すべての外部オプショナルプラグインをオフにした状態で、小説の生成・保存・
エクスポートが最速で完結することを保証する。
"""

from __future__ import annotations

import asyncio

import pytest

from src.core.plugin_registry import PluginRegistry


@pytest.fixture()
def all_plugins_disabled(monkeypatch):
    """全 ENABLE_* フラグを削除してプラグイン無効状態にする。"""
    for flag in ("ENABLE_MULTIMEDIA", "ENABLE_AUDIO_SYNTH", "ENABLE_SOCIAL_POSTING"):
        monkeypatch.delenv(flag, raising=False)
    return monkeypatch


class TestCoreWithoutPlugins:
    def test_registry_has_no_enabled_plugins(self, all_plugins_disabled):
        """プラグイン 0 件の状態であること。"""
        registry = PluginRegistry()
        enabled = [e.name for e in registry.list_plugins() if e.enabled]
        assert enabled == []

    def test_registry_load_all_noop(self, all_plugins_disabled):
        """プラグイン 0 件時、load_all() は空マップを返すこと。"""
        registry = PluginRegistry()
        assert registry.load_all() == {}

    def test_easy_mode_pipeline_factory_completes(self, all_plugins_disabled):
        """プラグイン 0 件の状態で create_easy_mode_pipeline が完結すること。"""
        from src.services.auto_workflow_pipeline import create_easy_mode_pipeline

        pipeline = create_easy_mode_pipeline()
        assert pipeline is not None

    def test_easy_mode_pipeline_execute_completes(self, all_plugins_disabled):
        """プラグイン 0 件の状態でパイプライン実行が完全成功すること。"""
        from src.easy_mode.pipeline import EasyModePipeline
        from src.shared.utils import StatusReporter

        pipeline = EasyModePipeline()
        reporter = StatusReporter.__new__(StatusReporter)  # type: ignore[attr-defined]
        reporter.report = lambda *args, **kwargs: None  # type: ignore[attr-defined]
        result = asyncio.run(pipeline.execute(theme="冒険", reporter=reporter))
        assert result["status"] == "done"

    def test_multimedia_router_not_registered(self, all_plugins_disabled):
        """プラグイン無効時、multimedia ルーターが登録されないこと。"""
        import importlib
        import sys

        sys.modules.pop("src.backend.server", None)
        sys.modules.pop("src.core.plugin_registry", None)
        server = importlib.import_module("src.backend.server")
        has_multimedia = any(
            getattr(route, "path", "").startswith("/multimedia")
            for route in server.app.routes
        )
        assert has_multimedia is False

    def test_multimedia_plugin_not_loaded(self, all_plugins_disabled):
        """プラグイン無効時、MultimediaPlugin がロードされないこと。"""
        registry = PluginRegistry()
        registry.load("multimedia")
        assert registry.get("multimedia") is None

    def test_audio_plugin_not_loaded(self, all_plugins_disabled):
        """プラグイン無効時、AudioPlugin がロードされないこと。"""
        registry = PluginRegistry()
        registry.load("audio")
        assert registry.get("audio") is None

    def test_social_posting_plugin_not_loaded(self, all_plugins_disabled):
        """プラグイン無効時、SocialPostingPlugin がロードされないこと。"""
        registry = PluginRegistry()
        registry.load("social_posting")
        assert registry.get("social_posting") is None

    def test_core_imports_fast_without_plugins(self, all_plugins_disabled):
        """プラグイン無効時もコアモジュールのインポートが正常なこと。"""
        from src.services import auto_workflow_pipeline  # noqa: F401
        from src.services import pipeline_base  # noqa: F401

        assert auto_workflow_pipeline is not None
        assert pipeline_base is not None
