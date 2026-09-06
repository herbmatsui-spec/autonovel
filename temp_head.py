import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import tempfile
import os
from pathlib import Path

from src.backend.database.core import (
    retry_with_logging,
    WorkspaceManager,
    DatabaseConnectionWrapper,
    DatabaseManager,
    init_db,
    get_db_manager,
    set_db_manager,
    SessionLocal,
    engine
)


class TestRetryWithLogging:
    """retry_with_logging デコレータのテスト"""
    
    @pytest.mark.asyncio
    async def test_retry_with_logging_success_on_first_try(self):
        """最初の試行で成功する場合のテスト"""
        call_count = 0
        
        @retry_with_logging(retries=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_logging_success_after_retries(self):
        """リトライ後に成功する場合のテスト"""
        call_count = 0
        
        @retry_with_logging(retries=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("temporary error")
            return "success"
        
        result = await func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_logging_final_failure(self):
        """最終的に失敗する場合のテスト"""
        call_count = 0
        
        @retry_with_logging(retries=2, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("persistent error")
        
        with pytest.raises(asyncio.TimeoutError, match="persistent error"):
            await func()
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_logging_non_retryable_exception(self):
        """リトライ対象外の例外のテスト"""
        call_count = 0
        
        @retry_with_logging(retries=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("non-retryable error")
        
        with pytest.raises(ValueError, match="non-retryable error"):
            await func()
        
        assert call_count == 1


class TestWorkspaceManager:
    """WorkspaceManager クラスのテスト"""
    
    def test_get_path_returns_correct_path(self):
        """get_path が正しいパスを返すことを確認"""
        with patch('src.backend.database.core.BASE_DIR', Path('/tmp/test')):
            result = WorkspaceManager.get_path("test.txt")
            assert result == "/tmp/test/test.txt"
    
    def test_list_backups_returns_sorted_list(self):
        """list_backups がソートされたリストを返すことを確認"""
        with patch('src.backend.database.core.BASE_DIR') as mock_base_dir:
            # Mock Path.glob to return specific backup files
            mock_path1 = Mock()
            mock_path1.stat().st_mtime = 1000
            mock_path2 = Mock()
            mock_path2.stat().st_mtime = 2000
            mock_path3 = Mock()
            mock_path3.stat().st_mtime = 1500
            
            mock_base_dir.glob.return_value = [mock_path1, mock_path2, mock_path3]
            
            result = WorkspaceManager.list_backups()
            assert len(result) == 3
            # Should be sorted by mtime descending (newest first)
            assert result[0] == mock_path2  # mtime=2000
            assert result[1] == mock_path3  # mtime=1500
            assert result[2] == mock_path1  # mtime=1000
    
def test_create_snapshot_creates_backup(self):
        """create_snapshot がバックアップを作成することを確認"""
        with patch('src.backend.database.core.BASE_DIR', Path('/tmp')):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('shutil.copy2') as mock_copy:
                    with patch('src.backend.database.core.logger') as mock_logger:
                        with patch('time.time', return_value=1234567890):
                            mock_src = Mock()
                            mock_dst = Mock()
                            mock_src.with_suffix.return_value = mock_dst
                            
                            with patch('pathlib.Path', return_value=mock_src):
                                result = WorkspaceManager.create_snapshot("/tmp/test.db")
                                
                                assert result == "/tmp/test.db.bak_1234567890.db"
                                mock_copy.assert_called_once_with(mock_src, mock_dst)
                                mock_logger.info.assert_called_once_with(
                                    "Snapshot created: test.db.bak_1234567890.db"
                                )
