"""
src/backend/routers/commercial.py — Commercial Pipeline API
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.backend.auth import require_api_key
from src.backend.database import get_db
from src.backend.database.models import PublicationScheduleDbModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.services.publishers import (
    get_credential_store,
    NarouCredentials,
    KakuyomuCredentials,
    KoboCredentials,
    KindleCredentials,
)

router = APIRouter(prefix="/commercial", tags=["commercial"])


class CommercialConfig(BaseModel):
    """商用化パイプライン設定"""

    series_config: dict[str, Any] = {}
    samples: list[dict[str, Any]] = []
    platforms: list[str] = ["kakuyomu", "naru"]  # デフォルトプラットフォーム
    do_publish: bool = False  # 実際に投稿を実行するか
    credentials: dict[str, dict[str, Any]] | None = None  # プラットフォーム別認証情報（オプション）


class PublishRequest(BaseModel):
    """投稿実行リクエスト"""

    book_id: int = Field(..., ge=1, description="書籍ID")
    platforms: list[str] = Field(
        default_factory=lambda: ["kakuyomu", "narou"], description="投稿先プラットフォーム"
    )
    episode_range: tuple[int, int] | None = Field(None, description="投稿対象話数範囲 (from, to)")
    episode_ids: list[int] | None = Field(None, description="投稿対象エピソードIDリスト")
    schedule: dict[str, Any] | None = Field(None, description="定期投稿スケジュール設定")
    credentials: dict[str, dict[str, Any]] | None = Field(
        None, description="プラットフォーム別認証情報（環境変数優先）"
    )


class PublishStatusRequest(BaseModel):
    """投稿ステータス取得リクエスト"""

    book_id: int = Field(..., ge=1)
    platform: str
    post_id: str


class PublicationScheduleCreate(BaseModel):
    book_id: int = Field(..., ge=1)
    platform: str = Field(..., pattern="^(narou|kakuyomu|kindle|kobo)$")
    episode_range: tuple[int, int]
    scheduled_at: datetime
    credentials_override: dict[str, Any] | None = None


class PublicationScheduleResponse(BaseModel):
    id: int
    book_id: int
    platform: str
    episode_range: tuple[int, int]
    scheduled_at: datetime
    status: str
    error_message: str | None = None
    created_at: datetime


@router.post("/schedules", response_model=PublicationScheduleResponse)
async def create_schedule(
    req: PublicationScheduleCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """
    投稿スケジュールを登録する。
    """
    try:
        schedule = PublicationScheduleDbModel(
            book_id=req.book_id,
            platform=req.platform,
            episode_range_start=req.episode_range[0],
            episode_range_end=req.episode_range[1],
            scheduled_at=req.scheduled_at,
            status="pending",
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        return PublicationScheduleResponse(
            id=schedule.id,
            book_id=schedule.book_id,
            platform=schedule.platform,
            episode_range=(schedule.episode_range_start, schedule.episode_range_end),
            scheduled_at=schedule.scheduled_at,
            status=schedule.status,
            error_message=schedule.error_message,
            created_at=schedule.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/schedules/{book_id}", response_model=list[PublicationScheduleResponse])
async def get_schedules(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """
    書籍ごとの投稿スケジュール一覧を取得する。
    """
    try:
        from sqlalchemy import select
        stmt = (
            select(PublicationScheduleDbModel)
            .where(PublicationScheduleDbModel.book_id == book_id)
            .order_by(PublicationScheduleDbModel.scheduled_at.desc())
        )
        result = await db.execute(stmt)
        schedules = result.scalars().all()

        return [
            PublicationScheduleResponse(
                id=s.id,
                book_id=s.book_id,
                platform=s.platform,
                episode_range=(s.episode_range_start, s.episode_range_end),
                scheduled_at=s.scheduled_at,
                status=s.status,
                error_message=s.error_message,
                created_at=s.created_at,
            )
            for s in schedules
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedules: {str(e)}")


@router.delete("/schedules/{schedule_id}", response_model=dict[str, Any])
async def cancel_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """
    投稿スケジュールを取り消す。
    ステータスが 'pending' の場合のみ取り消し可能。
    """
    try:
        from sqlalchemy import select
        
        # スケジュールの取得
        result = await db.execute(select(PublicationScheduleDbModel).where(PublicationScheduleDbModel.id == schedule_id))
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        if schedule.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Only pending schedules can be cancelled. Current status: {schedule.status}"
            )
        
        # ステータスを cancelled に更新
        schedule.status = "cancelled"
        await db.commit()
        await db.refresh(schedule)
        
        return {"success": True, "message": "Schedule cancelled successfully", "schedule_id": schedule_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancel schedule failed: {str(e)}")


@router.post("/schedules/{schedule_id}/run-now", response_model=dict[str, Any])
async def run_schedule_now(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """
    予約投稿を即時に実行する (Step 10).
    """
    try:
        from sqlalchemy import select
        from src.backend.tasks.commercial_tasks import execute_publication_task
        
        # スケジュールの存在確認
        result = await db.execute(select(PublicationScheduleDbModel).where(PublicationScheduleDbModel.id == schedule_id))
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        if schedule.status == "running":
            raise HTTPException(status_code=400, detail="Schedule is already running")
        
        # Hueyタスクを即時投入
        execute_publication_task(schedule_id)
        
        return {"success": True, "message": "Publication task triggered successfully", "schedule_id": schedule_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trigger run-now failed: {str(e)}")
        await db.commit()
        await db.refresh(schedule)
        
        return {"success": True, "message": "Schedule cancelled successfully", "schedule_id": schedule_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancel schedule failed: {str(e)}")


@router.post("/run", response_model=dict[str, Any])
async def run_commercial_pipeline(
    config: CommercialConfig, api_key: str = Depends(require_api_key)
):
    """
    Commercial Pipeline を実行するエンドポイント。

    Args:
        config: Commercial Config

    Returns:
        Executed pipeline result
    """
    try:
        # パイプライン実行
        pipeline = CommercialPipeline()

        # 認証情報準備
        credentials = None
        if config.credentials:
            creds_map = {}
            for platform, creds_dict in config.credentials.items():
                creds_class = _get_credentials_class(platform)
                creds_map[platform] = creds_class(**creds_dict)
            credentials = creds_map

        result = await pipeline.run(
            series_config=config.series_config,
            samples=config.samples,
            platforms=config.platforms,
            credentials=credentials,
            do_publish=config.do_publish,
        )

        # 結果を標準化して返却
        return {"success": True, "data": result, "trace_id": f"comm_{str(hash(str(config)))[:8]}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.post("/publish", response_model=dict[str, Any])
async def publish_commercial(request: PublishRequest, api_key: str = Depends(require_api_key)):
    """
    既存書籍のエピソードを指定プラットフォームへ投稿する。

    書籍・エピソードはDBから取得し、認証情報は環境変数/キーリング/暗号化ファイルから自動取得。
    credentialsパラメータで上書き指定も可能。

    Args:
        request: 投稿リクエスト

    Returns:
        投稿結果
    """
    try:
        from src.backend.services.commercial_helpers import _get_novel_data, _get_episodes_data

        # 1. 書籍・エピソードデータ取得（プラットフォームIDもまとめて取得）
        await _get_novel_data(request.book_id)
        episodes_data = await _get_episodes_data(request.book_id, request.episode_ids, request.platforms)

        if not episodes_data:
            raise HTTPException(status_code=404, detail="No episodes found for this book")

        # 3. 認証情報準備
        credentials = {}
        credential_store = get_credential_store()

        for platform in request.platforms:
            if request.credentials and platform in request.credentials:
                # リクエストで指定された認証情報を優先
                creds_class = _get_credentials_class(platform)
                credentials[platform] = creds_class(**request.credentials[platform])
            else:
                # ストアから取得
                credentials[platform] = credential_store.get(platform)

        # 4. 予約投稿または非同期タスク投入 (Step 50, 51)
        serializable_credentials = {}
        for p, cred in credentials.items():
            if cred is not None:
                if hasattr(cred, "__dict__"):
                    serializable_credentials[p] = {
                        k: v for k, v in cred.__dict__.items() if not k.startswith("_")
                    }
                elif isinstance(cred, dict):
                    serializable_credentials[p] = cred

        from src.backend.tasks.commercial_tasks import schedule_commercial_publish

        if request.schedule:
            # 予約投稿ジョブの登録 (Step 50, 51)
            # request.schedule が dict 形式の場合に ISO 文字列または datetime オブジェクトへ正規化して渡す
            publish_at = request.schedule
            if isinstance(publish_at, dict):
                # 辞書型（{"target_time": "..."} や {"publish_at": "..."}）の展開
                publish_at = publish_at.get("target_time") or publish_at.get("publish_at") or publish_at.get("at")
            
            job_info = schedule_commercial_publish(
                book_id=request.book_id,
                platforms=request.platforms,
                credentials=serializable_credentials,
                episode_ids=request.episode_ids,
                publish_at=publish_at,
            )
            return {
                "success": True,
                "status": "scheduled",
                "message": "Commercial publish scheduled successfully",
                "data": job_info,
            }

        # 即時投稿：Hueyタスクを直接キューイング (Step 51)
        from src.backend.tasks.commercial_tasks import publish_to_platforms_task
        task_result = publish_to_platforms_task(
            book_id=request.book_id,
            platforms=request.platforms,
            credentials=serializable_credentials,
            episode_ids=request.episode_ids,
        )
        task_id = str(task_result.id) if task_result else "mock-task-id"
        return {
            "success": True,
            "status": "queued",
            "message": "Commercial publish queued for immediate execution",
            "data": {
                "task_id": task_id,
                "book_id": request.book_id,
                "platforms": request.platforms,
                "status": "queued",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")


@router.get("/scheduled-tasks/{book_id}", response_model=dict[str, Any])
async def get_scheduled_publish_tasks(
    book_id: int, api_key: str = Depends(require_api_key)
) -> dict[str, Any]:
    """予約投稿ジョブの一覧を取得する (Step 56)."""
    from src.backend.tasks.commercial_tasks import get_scheduled_commercial_tasks
    tasks = get_scheduled_commercial_tasks(book_id)
    return {"success": True, "data": tasks}


@router.delete("/scheduled-tasks/{task_id}", response_model=dict[str, Any])
async def cancel_scheduled_publish_task(
    task_id: str, api_key: str = Depends(require_api_key)
) -> dict[str, Any]:
    """予約投稿ジョブを取り消す (Step 57)."""
    from src.backend.tasks.commercial_tasks import cancel_commercial_task
    cancelled = cancel_commercial_task(task_id)
    return {
        "success": cancelled,
        "task_id": task_id,
        "status": "cancelled" if cancelled else "not_found_or_already_run",
    }


@router.post("/publish/status", response_model=dict[str, Any])
async def get_publish_status(
    request: PublishStatusRequest, api_key: str = Depends(require_api_key)
):
    """
    投稿ステータスを取得する。

    Args:
        request: ステータス取得リクエスト

    Returns:
        投稿ステータス情報
    """
    try:
        from src.services.publishers import get_publisher, get_credential_store

        publisher = get_publisher(request.platform)
        credential_store = get_credential_store()
        credentials = credential_store.get(request.platform)

        await publisher.authenticate(credentials)
        status = await publisher.get_post_status(request.post_id, credentials)

        return {"success": True, "data": status}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/publish/records/{book_id}", response_model=dict[str, Any])
async def get_publish_records(book_id: int, api_key: str = Depends(require_api_key)):
    """
    書籍の投稿履歴を取得する。

    Args:
        book_id: 書籍ID

    Returns:
        投稿履歴リスト
    """
    try:
        from sqlalchemy import select
        from src.infrastructure.database.models.publish_record import PublishRecord
        from src.backend.database.uow import UnitOfWork
        from src.core.container import AppContainer

        async with UnitOfWork(AppContainer.db()) as uow:
            if uow.session is None:
                raise HTTPException(status_code=500, detail="Database session not available")
            result = await uow.session.execute(
                select(PublishRecord)
                .where(PublishRecord.book_id == book_id)
                .order_by(PublishRecord.episode_num, PublishRecord.platform)
            )
            records = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "id": r.id,
                    "episode_num": r.episode_num,
                    "platform": r.platform,
                    "post_id": r.post_id,
                    "post_url": r.post_url,
                    "status": r.status,
                    "error_message": r.error_message,
                    "published_at": r.published_at,
                    "updated_at": r.updated_at,
                }
                for r in records
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Records fetch failed: {str(e)}")


@router.get("/publish/platforms", response_model=list[dict[str, str]])
async def list_publish_platforms():
    """対応投稿プラットフォーム一覧を取得"""
    from src.services.publishers import list_publishers

    return list_publishers()


async def _save_publish_records(book_id: int, publish_results: dict[str, list]):
    """投稿結果をDBに保存"""
    from sqlalchemy.dialects.postgresql import insert
    from src.infrastructure.database.models.publish_record import PublishRecord
    from src.backend.database.uow import UnitOfWork
    from src.core.container import AppContainer

    now = int(datetime.utcnow().timestamp())

    records_to_insert = []
    for platform, results in publish_results.items():
        for episode, result in zip(
            # episodes_dataを再構築するか、PublishRecordから逆引き
            # ここでは簡易的にresultから情報を抽出
            [{"ep_num": i + 1} for i in range(len(results))],  # プレースホルダー
            results,
        ):
            if result.success and result.post_id:
                records_to_insert.append(
                    {
                        "book_id": book_id,
                        "episode_num": episode.get("ep_num", 0),
                        "platform": platform,
                        "post_id": result.post_id,
                        "post_url": result.url,
                        "status": "published",
                        "error_message": None,
                        "published_at": now,
                        "updated_at": now,
                    }
                )
            elif not result.success:
                records_to_insert.append(
                    {
                        "book_id": book_id,
                        "episode_num": episode.get("ep_num", 0),
                        "platform": platform,
                        "post_id": result.post_id or "failed",
                        "post_url": None,
                        "status": "failed",
                        "error_message": result.error,
                        "published_at": now,
                        "updated_at": now,
                    }
                )

    if records_to_insert:
        async with UnitOfWork(AppContainer.db()) as uow:
            if uow.session is None:
                return
            # UPSERT（ON CONFLICT DO UPDATE）
            for record in records_to_insert:
                stmt = insert(PublishRecord).values(**record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["book_id", "episode_num", "platform"],
                    set_={
                        "post_id": stmt.excluded.post_id,
                        "post_url": stmt.excluded.post_url,
                        "status": stmt.excluded.status,
                        "error_message": stmt.excluded.error_message,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                await uow.session.execute(stmt)
            await uow.session.commit()


def _get_credentials_class(platform: str):
    """プラットフォーム名から認証情報クラスを取得"""
    mapping = {
        "narou": NarouCredentials,
        "kakuyomu": KakuyomuCredentials,
        "kobo": KoboCredentials,
        "kindle": KindleCredentials,
    }
    cls = mapping.get(platform)
    if not cls:
        raise ValueError(f"Unknown platform: {platform}")
    return cls
