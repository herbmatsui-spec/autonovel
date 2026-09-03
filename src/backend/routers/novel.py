"""
src/backend/routers/novel.py — 小説制作関連APIエンドポイント
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.backend.auth import require_api_key
from src.models.api_schemas import (
    EpisodeListResponse,
    NovelReportResponse,
    NovelStatusResponse,
    ProduceNovelRequest,
    ProduceNovelResponse,
)
from src.services.novel_producer import NovelProducer
from src.services.report_generator import ReportGenerator

router = APIRouter(prefix="/api/novel", tags=["novel"])

# シングルトンプロデューサー（簡易実装）
producer = NovelProducer()
report_generator = ReportGenerator()


class BookScoreResponse(BaseModel):
    book_id: int
    chapter_number: int
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float
    evaluated_at: str | None = None


@router.post("/produce", response_model=ProduceNovelResponse)
async def produce_novel(req: ProduceNovelRequest, api_key: str = Depends(require_api_key)):
    """作品全話生成を開始するエンドポイント"""
    # プロジェクト作成
    from src.models.production_config import NovelProject

    project = NovelProject(
        title=req.title,
        genre=req.genre,
        synopsis=req.synopsis,
        keywords=req.keywords,
        target_episodes=req.target_episodes,
        target_word_count_per_episode=req.target_word_count,
        style_key=req.style_key,
        engine_key=req.engine_key,
    )
    producer.create_project(project)
    # 非同期で全話生成（バックグラウンドタスクは省略）
    try:
        await producer.generate_all_episodes(project_id=1)  # 仮にID 1 を使用
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ProduceNovelResponse(
        project_id=1,
        status="completed",
        message="全話生成が完了しました",
        token_usage_estimate=None,
    )


@router.get("/{project_id}/status", response_model=NovelStatusResponse)
async def get_novel_status(project_id: int):
    """作品ステータス取得"""
    progress = producer.get_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
    return NovelStatusResponse(
        project_id=project_id,
        status=progress.status,
        current_episode=progress.current_episode,
        total_episodes=progress.total_episodes,
        progress_percent=progress.progress_percent,
        message=progress.message,
        completed_episodes=progress.completed_eps,
    )


@router.get("/{project_id}/episodes", response_model=EpisodeListResponse)
async def list_episodes(project_id: int):
    """エピソード一覧取得"""
    episodes = producer.get_episodes()
    data: list[dict[str, Any]] = []
    for ep in episodes:
        data.append(
            {
                "ep_num": ep.ep_num,
                "title": ep.title,
                "word_count": ep.word_count,
                "quality_score": ep.quality_score,
            }
        )
    return EpisodeListResponse(episodes=data)


@router.get("/{project_id}/report", response_model=NovelReportResponse)
async def get_report(project_id: int):
    """制作レポート取得"""
    try:
        report = producer.generate_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Report を dict に変換（簡易）
    report_dict = report.dict()
    return NovelReportResponse(report=report_dict)


@router.get("/books/{book_id}/chapters/{chapter_number}/score", response_model=BookScoreResponse)
async def get_chapter_book_score(book_id: int, chapter_number: int):
    """指定章の BookScore を取得する"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository
        from sqlalchemy.ext.asyncio import AsyncSession

        # 簡易実装: リポジトリ経由で取得
        repo = DataRepository()
        session = repo._session_factory()  # type: ignore
        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)
        score_model = await calculator.get_latest_score(book_id, chapter_number)

        if score_model is None:
            raise HTTPException(status_code=404, detail="スコアが見つかりません")

        return BookScoreResponse(
            book_id=score_model.book_id,
            chapter_number=score_model.chapter_number,
            overall_score=score_model.overall_score,
            structure_score=score_model.structure_score,
            coherency_score=score_model.coherency_score,
            factual_grounding_score=score_model.factual_grounding_score,
            visual_textual_synergy_score=score_model.visual_textual_synergy_score,
            reader_experience_score=score_model.reader_experience_score,
            evaluated_at=score_model.evaluated_at.isoformat() if score_model.evaluated_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
