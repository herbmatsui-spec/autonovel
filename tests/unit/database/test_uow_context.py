import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.uow import UnitOfWork

@pytest.mark.asyncio
async def test_uow_commit_on_success():
    """正常終了時にコミットされることをテスト"""
    mock_session = AsyncMock()
    # Replace in_transaction with a regular Mock that returns False
    mock_session.in_transaction = MagicMock(return_value=False)
    mock_session.begin = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()
    
    mock_db = MagicMock()
    mock_db.get_session.return_value = mock_session
    
    
    uow = UnitOfWork(db=mock_db)
    
    # Check that session is initially None
    assert uow.session is None
    
    async with uow:
        # Inside the context, session should be set
        assert uow.session == mock_session
        # begin should have been called during __aenter__
        mock_session.begin.assert_awaited_once()
        
    # After the context, commit and close should have been called
    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_uow_rollback_on_failure():
    """例外発生時にロールバックされることをテスト"""
    mock_session = AsyncMock()
    # Replace in_transaction with a regular Mock that returns False
    mock_session.in_transaction = MagicMock(return_value=False)
    mock_session.begin = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    
    mock_db = MagicMock()
    mock_db.get_session.return_value = mock_session
    
    uow = UnitOfWork(db=mock_db)
    
    # 例外が発生した場合でもコンテキストは正常に終了するはず
    with pytest.raises(RuntimeError):
        async with uow:
            raise RuntimeError("DB Error")
            
    # ロールバックとクローズが呼ばれることを確認
    mock_session.rollback.assert_awaited_once()
    mock_session.close.assert_awaited_once()