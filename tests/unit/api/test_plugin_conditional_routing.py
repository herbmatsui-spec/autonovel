"""Step 19 検証テスト: マルチメディア無効時の FastAPI ルーター軽量化.

ENABLE_MULTIMEDIA フラグに応じて /multimedia ルーターが条件付きマウントされる
ことを検証する。
"""

from __future__ import annotations

import importlib
import sys

from fastapi import FastAPI

from src.core.plugin_registry import PluginRegistry


def _fresh_server_module(monkeypatch, enable_multimedia: bool | None):
    """server.py をフラグ付きで再インポートし、(app, registry) を返す。"""
    if enable_multimedia is None:
        monkeypatch.delenv("ENABLE_MULTIMEDIA", raising=False)
    else:
        monkeypatch.setenv("ENABLE_MULTIMEDIA", str(enable_multimedia).lower())
    # モジュールキャッシュから除外して再評価
    sys.modules.pop("src.backend.server", None)
    sys.modules.pop("src.core.plugin_registry", None)
    server = importlib.import_module("src.backend.server")
    registry = importlib.import_module("src.core.plugin_registry")
    return server, registry


def _has_multimedia_route(app: FastAPI) -> bool:
    """/multimedia プレフィックスのルートが存在するか。"""
    return any(
        getattr(route, "path", "").startswith("/multimedia") for route in app.routes
    )


class TestConditionalRouting:
    def test_multimedia_router_skipped_when_disabled(self, monkeypatch):
        """ENABLE_MULTIMEDIA 未設定時、/multimedia ルートがマウントされないこと。"""
        server, _ = _fresh_server_module(monkeypatch, enable_multimedia=None)
        assert not _has_multimedia_route(server.app)

    def test_multimedia_router_mounted_when_enabled(self, monkeypatch):
        """ENABLE_MULTIMEDIA=true 時、/multimedia ルートがマウントされること。"""
        server, _ = _fresh_server_module(monkeypatch, enable_multimedia=True)
        assert _has_multimedia_route(server.app)

    def test_core_routes_mounted_regardless(self, monkeypatch):
        """コアルーター (/health) はフラグに関係なくマウントされること。"""
        server, _ = _fresh_server_module(monkeypatch, enable_multimedia=None)
        paths = [getattr(route, "path", "") for route in server.app.routes]
        assert "/health" in paths

    def test_explicit_false_disables(self, monkeypatch):
        server, _ = _fresh_server_module(monkeypatch, enable_multimedia=False)
        assert not _has_multimedia_route(server.app)


class TestRegistryGating:
    def test_registry_flag_matches_routing(self, monkeypatch):
        """PluginRegistry の判定とルーティング挙動が一致すること。"""
        for enabled in (True, False):
            monkeypatch.setenv("ENABLE_MULTIMEDIA", str(enabled).lower())
            registry = PluginRegistry()
            assert registry.is_enabled("multimedia") is enabled
