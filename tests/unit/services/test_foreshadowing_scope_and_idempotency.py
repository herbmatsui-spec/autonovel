"""伏線スコープ判定と冪等登録の回帰テスト。"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from src.backend.database.models import Book
from src.backend.database.models_foreshadowing import ForeshadowingModel
from src.config.commercial_beat_sheet import get_scope_for_episode
from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository


class _AsyncSessionAdapter:
    """同期セッションを DbForeshadowingRepository が要求する AsyncSession 互換にアダプトする。"""

    def __init__(self, sync_session):
        self._s = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self._s.execute(statement, *args, **kwargs)

    async def flush(self):
        self._s.flush()

    def add(self, instance):
        self._s.add(instance)


def test_scope_comes_from_commercial_beats():
    assert get_scope_for_episode(1) == "short_term"
    assert get_scope_for_episode(20) == "long_term"
    assert get_scope_for_episode(35) == "long_term"
    assert get_scope_for_episode(40) == "short_term"


@pytest.mark.asyncio
async def test_add_if_absent_is_idempotent(real_db_manager):
    session = real_db_manager
    book = Book(title="冪等テスト")
    session.add(book)
    session.commit()

    repo = DbForeshadowingRepository(_AsyncSessionAdapter(session))
    first = await repo.add_if_absent(
        book_id=book.id, title="第1話: 伏線A", description="A", planted_episode=1
    )
    assert first is not None
    second = await repo.add_if_absent(
        book_id=book.id, title="第1話: 伏線A", description="A", planted_episode=1
    )
    assert second is None
    session.commit()
    rows = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_add_if_absent_allows_different_episodes(real_db_manager):
    session = real_db_manager
    book = Book(title="複数話テスト")
    session.add(book)
    session.commit()
    repo = DbForeshadowingRepository(_AsyncSessionAdapter(session))
    for ep in (1, 2, 3):
        created = await repo.add_if_absent(
            book_id=book.id, title=f"第{ep}話: 伏線", description="x", planted_episode=ep
        )
        assert created is not None
    session.commit()
    rows = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
    ).scalars().all()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_get_unresolved_by_scope_accepts_string(real_db_manager):
    session = real_db_manager
    book = Book(title="スコープ検索")
    session.add(book)
    session.commit()
    repo = DbForeshadowingRepository(_AsyncSessionAdapter(session))
    await repo.add_if_absent(
        book_id=book.id, title="長期", description="x", planted_episode=20, scope="long_term"
    )
    session.commit()
    found = await repo.get_unresolved_by_scope(book.id, "long_term")
    assert len(found) == 1
