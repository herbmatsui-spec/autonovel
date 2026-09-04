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
    trend_3ch: dict | None = None  # 直近3章のトレンド


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

        # トレンド情報取得（直近3章）
        trend_3ch = None
        all_scores = await book_score_repo.get_all_for_book(book_id)
        if all_scores:
            # 直近3章
            recent = all_scores[-3:] if len(all_scores) >= 3 else all_scores
            if len(recent) >= 2:
                avg_overall = sum(s.overall_score for s in recent) / len(recent)
                # 傾向: 最新と3章前の差分
                trend_slope = recent[-1].overall_score - recent[0].overall_score if len(recent) >= 2 else 0
                trend_3ch = {
                    "avg_overall_score": round(avg_overall, 2),
                    "trend_slope": round(trend_slope, 2),  # 正なら向上、負なら低下
                    "chapters_count": len(recent),
                    "recent_scores": [{"chapter": s.chapter_number, "overall": s.overall_score} for s in recent],
                }

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
            trend_3ch=trend_3ch,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PromotionEligibilityResponse(BaseModel):
    book_id: int
    eligible: bool
    avg_score: float
    trend_slope: float
    chapters_evaluated: int
    reason: str | None = None


@router.get("/books/{book_id}/promotion", response_model=PromotionEligibilityResponse)
async def check_promotion_eligibility(book_id: int):
    """かんたんモードから上級者Studioへの昇格判定を取得する"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository
        from sqlalchemy.ext.asyncio import AsyncSession

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore
        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)
        all_scores = await book_score_repo.get_all_for_book(book_id)

        if len(all_scores) < 3:
            return PromotionEligibilityResponse(
                book_id=book_id,
                eligible=False,
                avg_score=0.0,
                trend_slope=0.0,
                chapters_evaluated=len(all_scores),
                reason="3章以上の評価が必要です",
            )

        recent = all_scores[-3:]
        avg_overall = sum(s.overall_score for s in recent) / 3
        trend_slope = recent[-1].overall_score - recent[0].overall_score

        eligible = avg_overall >= 80.0 and trend_slope > 0
        reason = None
        if not eligible:
            if avg_overall < 80.0:
                reason = f"平均スコア {avg_overall:.1f} が 80.0 未満です"
            elif trend_slope <= 0:
                reason = f"スコア傾向が上昇していません (傾斜: {trend_slope:.1f})"

        # メトリクス記録
        try:
            from src.backend.observability.metrics import record_promotion_eligible
            record_promotion_eligible(book_id, eligible)
        except Exception:
            pass  # メトリクス失敗は無視

        return PromotionEligibilityResponse(
            book_id=book_id,
            eligible=eligible,
            avg_score=round(avg_overall, 2),
            trend_slope=round(trend_slope, 2),
            chapters_evaluated=3,
            reason=reason,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PDCAReportResponse(BaseModel):
    book_id: int
    plan: dict[str, Any]
    do: dict[str, Any]
    check: dict[str, Any]
    act: dict[str, Any]


@router.get("/books/{book_id}/pdca", response_model=PDCAReportResponse)
async def get_pdca_report(book_id: int):
    """書籍の PDCA レポートを取得する"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore
        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)
        report = await calculator.generate_pdca_report(book_id)

        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])

        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AlertResponse(BaseModel):
    book_id: int
    alerts: list[dict[str, Any]]


@router.get("/books/{book_id}/alerts", response_model=AlertResponse)
async def get_book_alerts(book_id: int):
    """書籍のスコアアラートを取得する"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore
        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)

        trend = await calculator.analyze_trend(book_id)

        if "error" in trend:
            return {"book_id": book_id, "alerts": []}

        alerts = []

        # スコア急落アラート（直近3章で15点以上低下）
        if trend.get("changepoints"):
            for cp in trend["changepoints"]:
                if cp["change"] < -15:
                    alerts.append({
                        "type": "score_drop",
                        "severity": "high",
                        "message": f"第{cp['chapter_index']}章でスコアが {abs(cp['change']):.1f} 点急落",
                        "chapter_index": cp["chapter_index"],
                        "details": cp,
                    })

        # 停滞アラート（傾斜がほぼゼロかつ平均70未満）
        if abs(trend.get("slope", 0)) < 0.5 and trend.get("avg_score", 0) < 70:
            alerts.append({
                "type": "stagnation",
                "severity": "medium",
                "message": f"スコアが停滞しています（平均: {trend['avg_score']:.1f}、傾斜: {trend['slope']:.2f}）",
                "avg_score": trend["avg_score"],
                "slope": trend["slope"],
            })

        # 異常値アラート（極端に低いスコア）
        if trend.get("latest_score", 100) < 50:
            alerts.append({
                "type": "anomaly",
                "severity": "critical",
                "message": f"最新章のスコアが極端に低いです: {trend['latest_score']:.1f}",
                "latest_score": trend["latest_score"],
            })

        # 改善停止アラート（5章以上改善なし）
        if trend.get("slope", 0) <= 0 and trend.get("chapters_evaluated", 0) >= 5:
            alerts.append({
                "type": "no_improvement",
                "severity": "medium",
                "message": f"{trend['chapters_evaluated']}章以上改善が見られません",
                "slope": trend["slope"],
            })

        return {"book_id": book_id, "alerts": alerts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
