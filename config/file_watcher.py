from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Protocol

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config.validator import ConfigValidator


class AppNotifier(Protocol):
    def toast_notify(self, key: str, message: str, icon: str) -> None:
        ...
    def reload_app(self) -> None:
        ...


class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, callback, notifier: AppNotifier):
        self.callback = callback
        self.notifier = notifier
        self.last_modified = {}
        self.debounce_delay = 1.0  # 1秒のデバウンス

    def on_modified(self, event):
        if event.is_directory:
            return

        # 設定ファイルのみを監視
        config_files = [
            "config/settings.toml",
            "config/models.yaml",
            "config/system_plugins.yaml",
            "config/tropes.json",
            "config/interaction_matrix.yaml",
            "config/domain_profiles/"
        ]

        file_path = event.src_path
        for config_file in config_files:
            if config_file.endswith("/"):
                if file_path.startswith(config_file):
                    self._schedule_callback()
                    return
            elif file_path == config_file:
                self._schedule_callback()
                return

    def _schedule_callback(self):
        """デバウンス用の遅延実行"""
        self.last_modified[time.time()] = True
        threading.Timer(self.debounce_delay, self._execute_callback).start()

    def _execute_callback(self):
        """実際のコールバックを実行"""
        # 最後の変更が1秒以上前に発生したか確認
        if not self.last_modified:
            return

        # 最新のタイムスタンプを取得
        latest_time = max(self.last_modified.keys())

        # 1秒以上経過しているか確認
        if time.time() - latest_time >= self.debounce_delay:
            # 全ての変更をクリア
            self.last_modified.clear()

            # バリデーションを実行
            try:
                ConfigValidator.validate_all()
                self.notifier.toast_notify("config_reload", "設定ファイルが更新されました。アプリをリロードします。", icon="🔄")
                self.notifier.reload_app()
            except Exception as e:
                self.notifier.toast_notify("config_error", f"設定ファイルの再読み込みに失敗しました: {str(e)}", icon="❌")


class ConfigFileWatcher:
    def __init__(self, notifier: AppNotifier):
        self.observer = Observer()
        self.handler = ConfigFileHandler(self._on_change, notifier)
        self.is_running = False

    def start(self):
        if self.is_running:
            return

        # 設定ファイルのディレクトリを監視
        config_dir = Path("config")
        self.observer.schedule(self.handler, str(config_dir), recursive=True)
        self.observer.start()
        self.is_running = True
        print("ConfigFileWatcher started.")

    def stop(self):
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            print("ConfigFileWatcher stopped.")

    def _on_change(self):
        pass

# アプリ起動時に自動で起動
class DefaultNotifier:
    def toast_notify(self, key: str, message: str, icon: str) -> None:
        UIStateStore.toast_notify(key, message, icon=icon)
    def reload_app(self) -> None:
        import streamlit as st
        st.experimental_rerun()

watcher = ConfigFileWatcher(DefaultNotifier())
watcher.start()

