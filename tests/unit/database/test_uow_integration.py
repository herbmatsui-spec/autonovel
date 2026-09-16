import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.uow import UnitOfWork

@pytest.mark.asyncio
async def test_uow_atomic_rollback_on_failure():
    mock_session = AsyncMock()
    mock_session.in_transaction = MagicMock(return_value=False)
    mock_session.begin = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_db = MagicMock()
    mock_db.get_session.return_value = mock_session

    uow = UnitOfWork(db=mock_db)

    # 複合処理中の例外シミュレーション
    with pytest.raises(RuntimeError):
        async with uow:
            uow.books.add = MagicMock()
            uow.plots.add = MagicMock()
            # 途中エラー
            raise RuntimeError("DB Write Crash")

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
    mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_uow_atomic_commit_on_success():
    mock_session = AsyncMock()
    mock_session.in_transaction = MagicMock(return_value=False)
    mock_session.add = MagicMock()
    mock_session.begin = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_db = MagicMock()
    mock_db.get_session.return_value = mock_session

    uow = UnitOfWork(db=mock_db)

    async with uow:
        # 正常に複数の処理を実行
        uow.stage_chroma_add("collection1", "doc1", "content", [0.1, 0.2])
        uow.stage_chroma_delete("collection1", ["doc0"])

    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()
