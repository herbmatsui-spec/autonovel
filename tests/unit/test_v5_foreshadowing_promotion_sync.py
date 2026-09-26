"""
test_v5_foreshadowing_promotion_sync.py
ウィザード保存およびStudio昇格時の伏線ステートマシン自動同期を検証するテスト。
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.backend.database.models import Book, Plot
from src.backend.database.models_foreshadowing import ForeshadowingModel
from src.domain.entities.easy_mode import PromotionRequest
from src.services.promotion_service import PromotionService


@pytest.mark.asyncio
async def test_promotion_service_foreshadowing_sync(real_db_manager):
    """昇格時にプロットの伏線メモがforeshadowingsテーブルへ同期されることを検証。"""
    session: Session = real_db_manager

    # 1. テスト用書籍とプロット作成
    book = Book(title="伏線同期テスト", mode="easy")
    session.add(book)
    session.commit()
    session.refresh(book)

    plot1 = Plot(
        book_id=book.id,
        branch_id=1,
        ep_num=1,
        title="第1話 旅立ち",
        detailed_blueprint="",
        foreshadowing_notes="古びたペンダントの謎（実は王家の紋章）",
        status="planned",
    )
    plot2 = Plot(
        book_id=book.id,
        branch_id=1,
        ep_num=2,
        title="第2話 襲撃",
        detailed_blueprint="",
        foreshadowing_notes="",
        status="planned",
    )
    plot3 = Plot(
        book_id=book.id,
        branch_id=1,
        ep_num=3,
        title="第3話 邂逅",
        detailed_blueprint="",
        foreshadowing_notes="謎の行商人が残した合言葉",
        status="planned",
    )
    plot4 = Plot(
        book_id=book.id,
        branch_id=1,
        ep_num=4,
        title="第4話 設計図のみ",
        detailed_blueprint="これは各話の設計図であり、伏線メモではない。",
        foreshadowing_notes="",
        status="planned",
    )
    session.add_all([plot1, plot2, plot3, plot4])
    session.commit()

    # 2. 昇格実行前の伏線件数は 0
    fs_before = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
    ).scalars().all()
    assert len(fs_before) == 0

    # 3. PromotionService で昇格実行
    class AsyncSessionAdapter:
        def __init__(self, sync_session):
            self._sync = sync_session
        async def execute(self, statement, *args, **kwargs):
            return self._sync.execute(statement, *args, **kwargs)
        async def commit(self):
            self._sync.commit()
        async def rollback(self):
            self._sync.rollback()
        def add(self, instance):
            self._sync.add(instance)
        def add_all(self, instances):
            self._sync.add_all(instances)
        async def flush(self):
            self._sync.flush()

    class MockDbManager:
        def __init__(self, s):
            self._s = AsyncSessionAdapter(s)
        def get_session(self):
            class _Ctx:
                def __init__(self, sess):
                    self.sess = sess
                async def __aenter__(self):
                    return self.sess
                async def __aexit__(self, *args):
                    pass
            return _Ctx(self._s)

    svc = PromotionService(db=MockDbManager(session))
    req = PromotionRequest(book_id=str(book.id))
    resp = await svc.promote_book(req)

    assert resp.success is True
    assert resp.state_token != ""

    # 4. 昇格後の検証: Book.mode が advanced になり、伏線が 2 件登録されていること
    session.refresh(book)
    assert book.mode == "advanced"

    fs_after = session.execute(
        select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id).order_by(ForeshadowingModel.planted_episode)
    ).scalars().all()

    assert len(fs_after) == 2
    assert fs_after[0].planted_episode == 1
    assert "古びたペンダントの謎" in fs_after[0].description
    assert fs_after[0].status == "planted"
    assert fs_after[0].scope == "short_term"

    assert fs_after[1].planted_episode == 3
    assert "謎の行商人が残した合言葉" in fs_after[1].description
    assert fs_after[1].status == "planted"
    assert fs_after[1].scope == "short_term"
