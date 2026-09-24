"""プラグインレジストリ (Step 18).

設定（環境変数・機能フラグ）に基づいてプラグインを動的にロード・無効化する仕組み。
コアバックエンドはこのレジストリ経由でのみオプショナルプラグインにアクセスする。
"""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from src.interfaces.plugin import BasePlugin, PluginProtocol

logger = logging.getLogger(__name__)

# 既知プラグイン名 -> (モジュールパス, クラス名, 有効化フラグ環境変数)
_BUILTIN_PLUGINS: dict[str, tuple[str, str, str]] = {
    "multimedia": ("src.plugins.multimedia.plugin", "MultimediaPlugin", "ENABLE_MULTIMEDIA"),
    "audio": ("src.plugins.audio.plugin", "AudioPlugin", "ENABLE_AUDIO_SYNTH"),
    "social_posting": (
        "src.plugins.social_posting.plugin",
        "SocialPostingPlugin",
        "ENABLE_SOCIAL_POSTING",
    ),
}


@dataclass
class PluginEntry:
    """レジストリ内のプラグインエントリ。"""

    name: str
    plugin: PluginProtocol | None = None
    enabled: bool = False
    loaded: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """設定に基づいてプラグインを動的にロード・管理するレジストリ.

    - :meth:`discover`: 環境変数フラグに基づき既知プラグインを探索
    - :meth:`load`: プラグインを初期化して有効化
    - :meth:`is_enabled`: プラグインが有効かどうか
    - :meth:`get`: 有効なプラグインインスタンスを取得
    - :meth:`shutdown_all`: 全有効プラグインを終了
    """

    def __init__(self) -> None:
        self._entries: dict[str, PluginEntry] = {}
        self._discover()

    # -------------------------------------------------- 探索

    def _discover(self) -> None:
        """環境変数フラグに基づき既知プラグインを探索する。

        ENABLE_* が明示的に "true" の場合のみ enabled=True とする。
        未設定 / "false" は無効（コアから分離された状態）。
        """
        for name, (module_path, class_name, flag_env) in _BUILTIN_PLUGINS.items():
            flag_value = os.getenv(flag_env, "").strip().lower()
            enabled = flag_value in ("1", "true", "yes", "on")
            self._entries[name] = PluginEntry(
                name=name,
                enabled=enabled,
                metadata={"module": module_path, "class": class_name, "flag": flag_env},
            )
            if not enabled:
                logger.debug("Plugin '%s' disabled (flag %s not set)", name, flag_env)

    # -------------------------------------------------- ロード

    def load(self, name: str) -> bool:
        """プラグインを動的にロードして初期化する.

        Returns:
            ロードと初期化に成功した（または既に有効な）場合 True。
        """
        entry = self._entries.get(name)
        if entry is None:
            logger.warning("Unknown plugin: %s", name)
            return False
        if not entry.enabled:
            logger.debug("Plugin '%s' is disabled; not loading", name)
            return False
        if entry.loaded and entry.plugin is not None:
            return True

        module_path = entry.metadata["module"]
        class_name = entry.metadata["class"]
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            plugin = plugin_class()
            if not isinstance(plugin, PluginProtocol):
                raise TypeError(
                    f"{module_path}.{class_name} does not satisfy PluginProtocol"
                )
            if not plugin.initialize():
                raise RuntimeError(f"Plugin '{name}' initialize() returned False")
            entry.plugin = plugin
            entry.loaded = True
            entry.error = None
            logger.info("Plugin '%s' loaded from %s", name, module_path)
            return True
        except Exception as exc:  # noqa: BLE001 - プラグイン失敗はコアを落とさない
            entry.plugin = None
            entry.loaded = False
            entry.error = str(exc)
            logger.warning("Failed to load plugin '%s': %s", name, exc)
            return False

    def load_all(self) -> dict[str, bool]:
        """有効な全プラグインをロードする。結果マップを返す。"""
        return {
            name: self.load(name)
            for name, entry in self._entries.items()
            if entry.enabled
        }

    # -------------------------------------------------- 状態確認

    def is_enabled(self, name: str) -> bool:
        """プラグインが有効かどうか（設定フラグ基準）。"""
        entry = self._entries.get(name)
        return entry is not None and entry.enabled

    def is_loaded(self, name: str) -> bool:
        """プラグインがロード・初期化済みかどうか。"""
        entry = self._entries.get(name)
        return entry is not None and entry.loaded and entry.plugin is not None

    def get(self, name: str) -> PluginProtocol | None:
        """有効なプラグインインスタンスを取得する。無効時は None。"""
        if not self.is_loaded(name):
            return None
        entry = self._entries[name]
        return entry.plugin

    def get_or_load(self, name: str) -> PluginProtocol | None:
        """必要ならロードしてから取得する。"""
        if self.is_enabled(name) and not self.is_loaded(name):
            self.load(name)
        return self.get(name)

    def list_plugins(self) -> list[PluginEntry]:
        """全エントリのスナップショットを返す。"""
        return list(self._entries.values())

    def known_plugins(self) -> list[str]:
        """既知プラグイン名のリストを返す。"""
        return list(_BUILTIN_PLUGINS.keys())

    # -------------------------------------------------- 終了

    def shutdown_all(self) -> None:
        """全ロード済みプラグインを終了し、リソースを解放する。"""
        for name, entry in self._entries.items():
            if entry.loaded and entry.plugin is not None:
                try:
                    entry.plugin.shutdown()
                    logger.info("Plugin '%s' shut down", name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error shutting down plugin '%s': %s", name, exc)
                finally:
                    entry.plugin = None
                    entry.loaded = False

    def disable(self, name: str) -> bool:
        """プラグインを明示的に無効化する。"""
        entry = self._entries.get(name)
        if entry is None:
            return False
        if entry.loaded and entry.plugin is not None:
            try:
                entry.plugin.shutdown()
            except Exception:  # noqa: BLE001
                pass
        entry.plugin = None
        entry.loaded = False
        entry.enabled = False
        return True


# モジュールレベルのデフォルトレジストリ（遅延生成）
_default_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """モジュールレベルのデフォルトレジストリを取得する（遅延生成）。"""
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        _default_registry = PluginRegistry()
    return _default_registry


def reset_plugin_registry() -> None:
    """デフォルトレジストリをリセットする（テスト用）。"""
    global _default_registry  # noqa: PLW0603
    if _default_registry is not None:
        _default_registry.shutdown_all()
    _default_registry = None
