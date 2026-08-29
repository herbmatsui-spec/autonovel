"""filesystem_memory/watcher.py - ファイル監視（watchdog）"""
import logging
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object  # type: ignore

logger = logging.getLogger(__name__)

if _WATCHDOG_AVAILABLE:

    class _Handler(FileSystemEventHandler):  # type: ignore[misc]
        def __init__(self, callback: Callable[[Path], None]):
            super().__init__()
            self.callback = callback

        def on_modified(self, event):
            if not event.is_directory:
                self.callback(Path(event.src_path))

else:

    class _Handler:  # type: ignore
        def __init__(self, callback):
            self.callback = callback


class WorkspaceWatcher:
    """ワークスペースディレクトリを監視し、変更をコールバックへ通知する"""

    def __init__(self, root: Path, callback: Callable[[Path], None]):
        self.root = root
        self.callback = callback
        self._observer = None

    def start(self):
        if not _WATCHDOG_AVAILABLE:
            logger.warning("watchdog not installed; file watching disabled")
            return
        handler = _Handler(self.callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.root), recursive=True)
        self._observer.start()

    def stop(self):
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
