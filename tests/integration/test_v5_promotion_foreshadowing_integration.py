"""昇格時の伏線同期の統合回帰テスト。

守ること:
  1) Plot.detailed_blueprint（設計図本文）は伏線として登録されない
  2) Plot.foreshadowing_notes（専用カラム）のみ登録される
  3) 2回昇格しても伏線数は増えない（冪等）
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from src.backend.database.models import Book, Plot
from src.backend.database.models_foreshadowing import ForeshadowingModel
from src.domain.entities.easy_mode import PromotionRequest
from src.services.promotion_service import PromotionService


class _SyncSessionAdapter:
    """PromotionService が期待する async セッションを、同期セッションで代用する。"""

    def __init__(self, sync_session):
        self._s = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self._s.execute(statement, *args, **kwargs)

    async def commit(self):
        self._s.commit()

    async def rollback(self):
        self._s.rollback()

    async def flush(self):
        self._s.flush()

    def add(self, instance):
        self._s.add(instance)


class _DbManager:
    def __init__(self, session):
        self._adapter = _SyncSessionAdapter(session)

    def get_session(self):
        session = self._adapter

        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()


async def _make_book_with_plots(session):
    book = Book(title="昇格統合テスト", mode="easy")
    session.add(book)
    session.commit()
    session.add_all([
        Plot(book_id=book.id, branch_id=1, ep_num=1, title="第1話",
             detailed_blueprint="各話の設計図本文", foreshadowing_notes="真の伏線", status="planned"),
        Plot(book_id=book.id, branch_id=1, ep_num=2, title="第2話",
             detailed_blueprint="各話の設計図本文2", foreshadowing_notes="", status="planned"),
    ])
    session.commit()
    return book


@pytest.mark.asyncio
async def test_promotion_syncs_only_foreshadowing_notes(real_db_manager):
    session = real_db_manager
    book = await _make_book_with_plots(session)
    svc = PromotionService(db=_DbManager(session))
    res = await svc.promote_book(PromotionRequest(book_id=str(book.id)))
    assert res.success is True

    rows = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].description == "真の伏線"
    assert rows[0].planted_episode == 1


@pytest.mark.asyncio
async def test_promotion_is_idempotent(real_db_manager):
    session = real_db_manager
    book = await _make_book_with_plots(session)
    svc = PromotionService(db=_DbManager(session))
    await svc.promote_book(PromotionRequest(book_id=str(book.id)))
    await svc.promote_book(PromotionRequest(book_id=str(book.id)))
    rows = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
    ).scalars().all()
    assert len(rows) == 1
