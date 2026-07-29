import os
import sys
from pathlib import Path
from typing import List, Callable, Optional
import time
import threading
import logging

logger = logging.getLogger(__name__)

# Windows-specific: use pywin32 for cross-process file change detection?
try:
    import win32file
    import win32con
    _HANDLE_INVALID = 0
except ImportError:
    # Fallback for non-Windows or when pywin32 not available
    _HANDLE_INVALID = None

class USBMonitor:
    """USBドライブ監視クラス（pywin32依存）"""
    def __init__(self, paths: List[str], callback: Callable[[Path, str], None]):
        """
        Args:
            paths: 監視対象のパスリスト
            callback: ファイルイベント発生時に呼び出される関数
                      シグネチャ: callback(str file_path, str event_type)
        """
        self.paths = [Path(p) for p in paths if Path(p).exists()]
        
        self.callback = callback
        self._observer = None
        self._stop_event = threading.Event()
        self._thread = None
        self._is_running = False

    def start(self) -> None:
        """監視を開始する"""
        if self._is_running:
            logger.debug("監視はすでに開始済みです。")
            return
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        logger.info(f"USB監視開始。監視対象パス: {[str(p) for p in self.paths]}")

    def stop(self) -> None:
        """監視を停止する"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._is_running = False
        logger.info("USB監視停止")

    def _monitor_loop(self) -> None:
        """監視用スレッド実行メソッド"""
        import time
        
        try:
            while not self._stop_event.is_set():
                for path in self.paths:
                    if not path.exists():
                        continue
                    
                    for pdf_file in path.rglob("*.pdf"):
                        try:
                            if pdf_file.stat().st_size == 0:
                                continue
                                
                            change_type = "created"
                            self.callback(str(pdf_file), change_type)
                            logger.debug(f"イベント検知: {change_type} - {pdf_file}")
                            
                            time.sleep(30.0)
                        except (OSError, PermissionError) as e:
                            logger.debug(f"ファイルアクセスエラー: {e}")
                            continue
                
                time.sleep(1.0)
        except Exception as e:
            logger.error(f"監視スレッドでエラーが発生: {e}")
        finally:
            logger.debug("監視スレッド終了")

    @staticmethod
    def is_ready_for_processing(file_path: Path, timeout_seconds: float = 2.0) -> bool:
        """
        ファイルが完全に書き込み終了したかを判定する
        """
        if not file_path.exists():
            return False
            
        initial_size = file_path.stat().st_size
        if initial_size == 0:
            return False
            
        start_time = time.time()
        has_changed = False
        
        while time.time() - start_time < timeout_seconds:
            time.sleep(0.1)
            current_size = file_path.stat().st_size
            if current_size != initial_size:
                initial_size = current_size
                has_changed = True
                
        return not has_changed

    @staticmethod
    def get_safe_filename(name: str, include_timestamp: bool = True) -> str:
        """ファイル名に利用できない文字を除去した安全な名前を生成"""
        import re
        stem, ext = os.path.splitext(name)
        
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', stem)
        sanitized = re.sub(r'\s+', '_', sanitized).strip('_')
        
        if include_timestamp:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            suffix = f"_{timestamp}{ext}"
            max_stem_len = 255 - len(suffix)
            if max_stem_len > 0 and len(sanitized) > max_stem_len:
                sanitized = sanitized[:max_stem_len]
            return f"{sanitized}{suffix}"
        
        max_stem_len = 255 - len(ext)
        if max_stem_len > 0 and len(sanitized) > max_stem_len:
            sanitized = sanitized[:max_stem_len]
        return f"{sanitized}{ext}"

is_ready_for_processing = USBMonitor.is_ready_for_processing
get_safe_filename = USBMonitor.get_safe_filename

def create_usb_monitor(paths: List[str], callback: Callable[[Path, str], None]) -> USBMonitor:
    """USB監視インスタンスを作成するファクトリー関数"""
    return USBMonitor(paths, callback)

# デバッグ用の簡易デモ関数（実装時は非削除）
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    def dummy_callback(file_path: Path, event_type: str):
        print(f"[DEBUG] {event_type.upper()}: {file_path}")
    
    monitor = create_usb_monitor(sys.argv[1:] if len(sys.argv) > 1 else ["E:\\"])
    monitor.start()
    
    try:
        # 無限ループで待機（デモ用）
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()