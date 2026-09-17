"""伏線リポジトリ（DB永続化版）の単体テスト。

AsyncMockでSQLAlchemy AsyncSessionをモックし、
DbForeshadowingRepository の各メソッドの動作を検証する。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository


@pytest.mark.asyncio
async def test_foreshadowing_repo_get_unresolved():
    """未回収伏線の取得を検証"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_foreshadowing = MagicMock(id=1, title="謎の剣", status="planted", planted_episode=3)
    mock_result.scalars.return_value.all.return_value = [mock_foreshadowing]
    mock_db.execute.return_value = mock_result

    repo = DbForeshadowingRepository(mock_db)
    items = await repo.get_unresolved(book_id=1)

    assert len(items) == 1
    assert items[0].title == "謎の剣"
    assert items[0].status == "planted"
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_foreshadowing_repo_add():
    """伏線の新規設置を検証"""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()

    repo = DbForeshadowingRepository(mock_db)
    result = await repo.add(
        book_id=1,
        title="消えた手紙",
        description="第5話で主人公が見つけた手紙が突然消えた",
        planted_episode=5,
        target_episode=12,
    )

    assert result.title == "消えた手紙"
    assert result.planted_episode == 5
    assert result.status == "planted"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_foreshadowing_repo_resolve():
    """伏線の回収更新を検証"""
    mock_db = AsyncMock()
    mock_exec_result = MagicMock()
    mock_exec_result.rowcount = 1
    mock_db.execute.return_value = mock_exec_result

    repo = DbForeshadowingRepository(mock_db)
    success = await repo.resolve(foreshadowing_id=1, episode_num=10)

    assert success is True
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_foreshadowing_repo_resolve_not_found():
    """存在しない伏線の回収は False を返す"""
    mock_db = AsyncMock()
    mock_exec_result = MagicMock()
    mock_exec_result.rowcount = 0
    mock_db.execute.return_value = mock_exec_result

    repo = DbForeshadowingRepository(mock_db)
    success = await repo.resolve(foreshadowing_id=9999, episode_num=10)

    assert success is False


@pytest.mark.asyncio
async def test_foreshadowing_repo_get_balance():
    """伏線バランス集計を検証"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("planted", 5),
        ("progressed", 2),
        ("resolved", 3),
    ]
    mock_db.execute.return_value = mock_result

    repo = DbForeshadowingRepository(mock_db)
    balance = await repo.get_balance(book_id=1)

    assert balance["planted"] == 5
    assert balance["progressed"] == 2
    assert balance["resolved"] == 3
    assert balance["abandoned"] == 0
    assert balance["active"] == 7  # planted + progressed


@pytest.mark.asyncio
async def test_foreshadowing_repo_get_overdue():
    """期限超過伏線の取得を検証"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    overdue = MagicMock(id=2, title="忘れられた約束", status="planted", target_episode=8)
    mock_result.scalars.return_value.all.return_value = [overdue]
    mock_db.execute.return_value = mock_result

    repo = DbForeshadowingRepository(mock_db)
    items = await repo.get_overdue(book_id=1, current_episode=12)

    assert len(items) == 1
    assert items[0].title == "忘れられた約束"
