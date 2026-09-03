"""
routers/system.py - システム状態・耐障害モード API

DB/Gemini の到達性とオフラインモード状態を報告する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import resilience

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
async def system_status() -> dict[str, Any]:
    """システム全体の耐障害ステータスを返す。"""
    return resilience.get_system_status()


@router.get("/offline")
async def offline_flag() -> dict[str, Any]:
    """オフラインモード有効状態を返す。"""
    return {
        "offline_mode_enabled": resilience.is_offline_mode_enabled(),
        "cache_first": resilience.is_offline_mode_enabled(),
    }


@router.post("/admin/book_score/recalc")
async def recalc_all_book_scores() -> dict[str, Any]:
    """全書籍の BookScore を再計算する（管理者用）"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository
        from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
        from sqlalchemy import select

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore

        # 全書籍IDを取得
        from src.infrastructure.database.models.book import Book as BookModel
        books_result = await session.execute(select(BookModel.id))
        book_ids = [row[0] for row in books_result.fetchall()]

        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)

        recalculated = 0
        for book_id in book_ids:
            # 該当書籍の全章を取得
            from src.infrastructure.database.models.chapter import Chapter as ChapterModel
            chapters_result = await session.execute(
                select(ChapterModel.ep_num).where(ChapterModel.book_id == book_id)
            )
            chapter_numbers = [row[0] for row in chapters_result.fetchall()]

            for chapter_number in chapter_numbers:
                # 既存スコアを削除
                await session.execute(
                    select(BookScoreModel).where(
                        BookScoreModel.book_id == book_id,
                        BookScoreModel.chapter_number == chapter_number,
                    ).delete()
                )
                # 再計算（プレースホルダー実装）
                from src.agents.orchestrator import AgentContext
                ctx = AgentContext(book_id=book_id, branch_id=1, ep_num=chapter_number, artifacts={})
                await calculator.calculate(book_id=book_id, chapter_number=chapter_number, ctx=ctx)
                recalculated += 1

        return {"status": "success", "recalculated_count": recalculated}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
