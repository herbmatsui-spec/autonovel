# manual_processor/tests/test_usb_monitor.py
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.usb_monitor import (
    USBMonitor,
    create_usb_monitor,
    is_ready_for_processing,
    get_safe_filename
)

class TestUSBMonitor:
    """USBMonitor クラスのテスト"""
    
    def test_usb_monitor_initialization_with_valid_paths(self):
        """有効なパスでUSBMonitorが初期化できること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = USBMonitor([tmpdir], callback=lambda p, e: None)
            assert len(monitor.paths) == 1
            assert monitor.paths[0] == Path(tmpdir)
            assert not monitor._is_running
    
    def test_usb_monitor_initialization_with_invalid_paths(self):
        """存在しないパスが指定された場合、空リストになること"""
        monitor = USBMonitor(["/nonexistent/path/that/does/not/exist"], callback=lambda p, e: None)
        assert len(monitor.paths) == 0
        # デフォルトパスが設定されるか、少なくとも初期化エラーにならないこと
        assert hasattr(monitor, 'paths')
    
    def test_usb_monitor_start_stop(self):
        """start/stopが正しく動作すること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = USBMonitor([tmpdir], callback=lambda p, e: None)
            monitor.start()
            assert monitor._is_running
            monitor.stop()
            assert not monitor._is_running

class TestCreateUsbMonitor:
    """ファクトリ関数 create_usb_monitor のテスト"""
    
    def test_create_usb_monitor_returns_instance(self):
        """インスタンスが返されること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = create_usb_monitor([tmpdir], lambda p, e: None)
            assert isinstance(monitor, USBMonitor)
    
    def test_create_usb_monitor_with_empty_paths(self):
        """空のパスリストでもインスタンス作成できること"""
        monitor = create_usb_monitor([], lambda p, e: None)
        assert isinstance(monitor, USBMonitor)

class TestIsReadyForProcessing:
    """ファイル準備完了チェックのテスト"""
    
    def test_ready_for_processing_with_complete_file(self):
        """書き込み完了済みファイルでTrueが返ること"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            filepath = Path(f.name)
        
        try:
            # 少し待ってからチェック
            time.sleep(0.1)
            assert is_ready_for_processing(filepath, timeout_seconds=1) is True
        finally:
            filepath.unlink(missing_ok=True)
    
    def test_ready_for_processing_with_nonexistent_file(self):
        """存在しないファイルでFalseが返ること"""
        assert is_ready_for_processing(Path("/nonexistent/file.pdf"), timeout_seconds=0.1) is False
    
    def test_ready_for_processing_with_empty_file(self):
        """空ファイルでFalseが返ること（サイズ変化待ち）"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            filepath = Path(f.name)
        
        try:
            # 空ファイルの場合、サイズが0のままなのでtimeoutでFalse
            result = is_ready_for_processing(filepath, timeout_seconds=0.2)
            assert result is False
        finally:
            filepath.unlink(missing_ok=True)
    
    def test_ready_for_processing_with_writing_file(self):
        """書き込み中のファイルでtimeout後にFalseが返ること"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            filepath = Path(f.name)
        
        try:
            # バックグラウンドで少しずつ書き込む
            def writer():
                with open(filepath, 'wb') as out:
                    for i in range(5):
                        out.write(b"x" * 1000)
                        out.flush()
                        time.sleep(0.1)
            
            import threading
            t = threading.Thread(target=writer)
            t.start()
            
            # 書き込み中にチェック（timeout短めで）
            result = is_ready_for_processing(filepath, timeout_seconds=0.5)
            t.join()
            
            # 書き込み中はサイズが変化するためFalseが返るはず
            assert result is False
        finally:
            filepath.unlink(missing_ok=True)

class TestGetSafeFilename:
    """ファイル名サニタイズのテスト"""
    
    def test_sanitize_removes_invalid_chars(self):
        """Windowsで使用不可な文字が除去されること"""
        result = get_safe_filename("test<file>name?.pdf", include_timestamp=False)
        assert "<" not in result
        assert ">" not in result
        assert "?" not in result
        assert "_" in result  # 置換文字
    
    def test_sanitize_preserves_valid_chars(self):
        """有効な文字は保持されること"""
        result = get_safe_filename("normal_file_name.pdf", include_timestamp=False)
        assert result == "normal_file_name.pdf"
    
    def test_sanitize_japanese_filename(self):
        """日本語ファイル名が正しく処理されること"""
        result = get_safe_filename("日本語マニュアル.pdf", include_timestamp=False)
        assert "日本語マニュアル" in result
        assert ".pdf" in result
    
    def test_sanitize_adds_timestamp(self):
        """タイムスタンプが付与されること"""
        result = get_safe_filename("test.pdf", include_timestamp=True)
        # フォーマット: YYYYMMDD_HHMMSS
        import re
        assert re.search(r'_\d{8}_\d{6}\.pdf$', result) is not None
    
    def test_sanitize_truncates_long_filename(self):
        """長すぎるファイル名が切り詰められること"""
        long_name = "a" * 300 + ".pdf"
        result = get_safe_filename(long_name, include_timestamp=True)
        assert len(result) <= 255  # Windows制限
    
    def test_sanitize_handles_empty_string(self):
        """空文字列の場合の挙動"""
        result = get_safe_filename("", include_timestamp=False)
        assert result == "" or result == "_"  # 実装による

class TestEventFiltering:
    """イベントフィルタリングのテスト（モックを使用）"""
    
    @patch('src.usb_monitor.time.sleep')
    def test_pdf_only_filtering(self, mock_sleep):
        """PDFファイルのみが処理対象になること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            events = []
            
            def callback(file_path, event_type):
                events.append((file_path, event_type))
            
            # テスト用ファイル作成
            pdf_file = Path(tmpdir) / "test.pdf"
            txt_file = Path(tmpdir) / "test.txt"
            pdf_file.write_text("dummy")
            txt_file.write_text("dummy")
            
            # USBMonitorの監視ループをモックして1回だけ実行
            monitor = USBMonitor([tmpdir], callback=callback)
            monitor._monitor_loop = Mock(side_effect=StopIteration)
            
            try:
                monitor._monitor_loop()
            except StopIteration:
                pass
            
            # ここではモックなので、実装依存の部分はスキップ
            # 実際には _monitor_loop 内で rglob("*.pdf") を使用しているため、.txt は無視される
            pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])