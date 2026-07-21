"""
src/backend/routers/novel.py — 小説制作関連APIエンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from src.models.api_schemas import (
    ProduceNovelRequest,
    ProduceNovelResponse,
    NovelStatusResponse,
    EpisodeListResponse,
    NovelReportResponse,
)
from src.services.novel_producer import NovelProducer
from src.services.report_generator import ReportGenerator
from src.backend.auth import require_api_key

router = APIRouter(prefix="/api/novel", tags=["novel"])

# シングルトンプロデューサー（簡易実装）
producer = NovelProducer()
report_generator = ReportGenerator()


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
    data: List[Dict[str, Any]] = []
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
