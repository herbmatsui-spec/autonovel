"""
src/backend/routers/commercial.py — Commercial Pipeline API
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.backend.auth import require_api_key
from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.services.publishers import (
    get_credential_store,
    PublisherCredentials,
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
    schedule: dict[str, Any] | None = Field(None, description="定期投稿スケジュール設定")
    credentials: dict[str, dict[str, Any]] | None = Field(
        None, description="プラットフォーム別認証情報（環境変数優先）"
    )


class PublishStatusRequest(BaseModel):
    """投稿ステータス取得リクエスト"""

    book_id: int = Field(..., ge=1)
    platform: str
    post_id: str


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
        return {"success": True, "data": result, "trace_id": f"comm_{hash(str(config))[:8]}"}

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
        from sqlalchemy import select
        from src.backend.database.models import Book, Chapter
        from src.backend.database.uow import UnitOfWork
        from src.core.container import AppContainer

        # 1. 書籍・エピソード取得
        async with UnitOfWork(AppContainer.db()) as uow:
            book = await uow.session.execute(select(Book).where(Book.id == request.book_id))
            book_row = book.scalar_one_or_none()
            if book_row is None:
                raise HTTPException(status_code=404, detail=f"Book {request.book_id} not found")

            # エピソード取得
            chapters_query = (
                select(Chapter).where(Chapter.book_id == request.book_id).order_by(Chapter.ep_num)
            )
            if request.episode_range:
                from_ep, to_ep = request.episode_range
                chapters_query = chapters_query.where(
                    Chapter.ep_num >= from_ep, Chapter.ep_num <= to_ep
                )

            chapters_result = await uow.session.execute(chapters_query)
            chapters = chapters_result.scalars().all()

            if not chapters:
                raise HTTPException(status_code=404, detail="No episodes found for this book")

        # 2. 小説データ構築
        novel_data = {
            "title": book_row.title,
            "synopsis": book_row.synopsis or book_row.concept or "",
            "genre": getattr(book_row, "genre", "general"),
            "tags": getattr(book_row, "tags", []),
            "is_adult": bool(getattr(book_row, "sanctuary_integrity", 100) < 100),
        }

        episodes_data = []
        for ch in chapters:
            episodes_data.append(
                {
                    "ep_num": ch.ep_num,
                    "title": ch.title,
                    "content": ch.content or "",
                    "summary": getattr(ch, "summary", ""),
                    # 既存投稿IDがある場合は含める
                    **{
                        f"{p}_post_id": getattr(ch, f"{p}_post_id", None) for p in request.platforms
                    },
                    **{
                        f"{p}_post_url": getattr(ch, f"{p}_post_url", None)
                        for p in request.platforms
                    },
                }
            )

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

        # 4. パイプラインで投稿実行
        pipeline = CommercialPipeline()
        publish_results = await pipeline._publish_to_platforms(
            novel=novel_data,
            episodes=episodes_data,
            platforms=request.platforms,
            credentials=credentials,
        )

        # 5. 結果をDBに保存
        await _save_publish_records(request.book_id, publish_results)

        # 6. スケジュール設定がある場合はジョブ登録（将来実装）
        if request.schedule:
            # TODO: APSchedulerでジョブ登録
            pass

        # レスポンス整形
        response_data = {
            "book_id": request.book_id,
            "published_episodes": len(episodes_data),
            "platforms": {},
        }

        for platform, results in publish_results.items():
            success_count = sum(1 for r in results if r.success)
            response_data["platforms"][platform] = {
                "success": success_count,
                "failed": len(results) - success_count,
                "details": [
                    {
                        "episode": ep.get("ep_num"),
                        "success": r.success,
                        "post_id": r.post_id,
                        "url": r.url,
                        "error": r.error,
                    }
                    for ep, r in zip(episodes_data, results)
                ],
            }

        return {"success": True, "data": response_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")


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
        from src.backend.database.models import PublishRecord
        from src.backend.database.uow import UnitOfWork
        from src.core.container import AppContainer

        async with UnitOfWork(AppContainer.db()) as uow:
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
    from sqlalchemy import insert
    from src.backend.database.models import PublishRecord
    from src.backend.database.uow import UnitOfWork
    from src.core.container import AppContainer
    from datetime import datetime

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
