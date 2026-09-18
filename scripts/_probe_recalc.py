"""一時検証スクリプト: recalc_all_book_scores のデバッグ3（実モデル使用）。"""
import sys
import asyncio
import traceback

sys.path.insert(0, "e:/hhh")

from unittest.mock import MagicMock, AsyncMock  # noqa: E402

session = MagicMock()
session.__aenter__ = AsyncMock(return_value=session)
session.__aexit__ = AsyncMock(return_value=False)

books_result = MagicMock()
books_result.fetchall.return_value = [(1,), (2,)]
chapters_result = MagicMock()
chapters_result.fetchall.return_value = [(1,), (2,), (3,)]
session.execute = AsyncMock(side_effect=[books_result] + [chapters_result] * 2)

import pytest  # noqa: E402


async def main():
    from src.backend.routers.system import recalc_all_book_scores

    with pytest.MonkeyPatch.context() as m:
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        import src.services.book_score_service as bss
        calculator = MagicMock()
        calculator.calculate = AsyncMock(return_value=MagicMock())
        m.setattr(bss, "BookScoreCalculator", lambda repository=None: calculator)

        # 手動で recalc_chapter 相当の処理を実行して例外を特定
        from sqlalchemy import delete, select
        from src.backend.database.models import Book as BookModel
        from src.backend.database.models import Chapter as ChapterModel
        from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
        from src.agents.orchestrator import AgentContext
        try:
            books_result2 = await session.execute(select(BookModel.id))
            ids = [row[0] for row in books_result2.fetchall()]
            print("book ids:", ids)
            stmt = delete(BookScoreModel).where(
                BookScoreModel.book_id == 1,
                BookScoreModel.chapter_number == 1,
            )
            print("delete stmt ok")
            await session.execute(stmt)
            print("session.execute ok")
            ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
            await calculator.calculate(book_id=1, chapter_number=1, ctx=ctx)
            print("calculate ok")
        except Exception:
            traceback.print_exc()


asyncio.run(main())
