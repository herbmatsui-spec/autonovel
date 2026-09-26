"""40話ビートシート取得・編集APIエンドポイント（SSOT接続・非同期タスク発行版）。"""
from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.backend.auth import get_current_user
from src.backend.database.models import Book, Branch, Plot, User
from src.backend.database.uow import UnitOfWork
from src.backend.security.owner_guard import verify_book_ownership
from src.models.beat_sheet import EpisodeBeat

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/commercial/planning",
    tags=["commercial-planning"],
    dependencies=[Depends(get_current_user)],
)


class BeatSheetResponse(BaseModel):
    """40話ビートシートのレスポンス（要素は SSOT の EpisodeBeat）。"""

    items: list[EpisodeBeat]


class BeatSheetGenerateRequest(BaseModel):
    """40話ビートシート生成リクエスト。"""

    book_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    synopsis: str = Field(min_length=1)
    genre: str = Field(default="fantasy", max_length=100)
    target_episodes: int = Field(default=40, ge=1, le=40)
    branch_id: int = Field(default=1, ge=1)


class BeatSheetTaskResponse(BaseModel):
    """タスク発行結果。"""

    task_id: str
    book_id: int
    success: bool = True


def _generate_task_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _plot_to_episode_beat(p: Plot) -> EpisodeBeat:
    """Plot ORM → SSOT の EpisodeBeat へ変換する（tension は 0-100 → 0.0-1.0）。"""
    target = p.target_tension
    if target is None:
        tension = p.tension if p.tension is not None else 50
        target = round(float(tension) / 100.0, 2)
    return EpisodeBeat(
        ep_num=int(p.ep_num),
        phase=p.current_chain_phase or "Setup",
        mission=p.summary or p.title or f"第{p.ep_num}話",
        tension_target=round(float(target), 2),
        visual_scene_focus=p.one_line_summary or p.title or "",
    )


async def _create_book_for_beat_sheet(
    request: BeatSheetGenerateRequest,
    current_user: User,
) -> int:
    """新規作成: Book を1件作成する（Branch も同時に作る）。"""
    from src.core.container import AppContainer

    if getattr(current_user, "id", None) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証ユーザー情報を取得できません",
        )
    async with UnitOfWork(AppContainer.db()) as uow:
        book = Book(
            user_id=current_user.id,
            title=request.title,
            genre=request.genre,
            synopsis=request.synopsis,
            target_eps=request.target_episodes,
        )
        uow.session.add(book)
        await uow.session.flush()
        branch = Branch(book_id=book.id, name="main", fork_ep_num=0)
        uow.session.add(branch)
        return int(book.id)


@router.get("/{book_id}", response_model=BeatSheetResponse)
async def get_beat_sheet(
    book_id: int,
    current_user: User = Depends(get_current_user),
) -> BeatSheetResponse:
    """書籍IDに紐づく40話ビートシートを取得する。

    存在しない場合は404を返す。
    """
    from src.core.container import AppContainer

    await verify_book_ownership(book_id, current_user, AppContainer.db())
    try:
        async with UnitOfWork(AppContainer.db()) as uow:
            stmt = select(Plot).where(Plot.book_id == book_id).order_by(Plot.ep_num)
            result = await uow.session.execute(stmt)
            plots = result.scalars().all()

        if not plots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ビートシートが未生成です（book_id={book_id}）。先に /generate を呼んでください。",
            )

        items = [_plot_to_episode_beat(p) for p in plots]
        return BeatSheetResponse(items=items)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get beat sheet: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ビートシートの取得に失敗しました",
        ) from exc


@router.post("/generate", response_model=BeatSheetTaskResponse)
async def generate_beat_sheet(
    request: BeatSheetGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """ビートシート生成をタスクとして発行する（同期実行しない）。"""
    from src.backend.task_helpers import create_task
    from src.backend.tasks import execute_service_workflow

    book_id = request.book_id
    if book_id is None:
        book_id = await _create_book_for_beat_sheet(request, current_user)

    task_id = _generate_task_id("commercial_beats")
    await create_task(task_id, "40話ビートシートを生成中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=None,
        config_dict={},
        method_name="commercial_beat_sheet_workflow",
        kwargs={
            "book_id": book_id,
            "title": request.title,
            "synopsis": request.synopsis,
            "genre": request.genre,
            "target_episodes": request.target_episodes,
            "branch_id": request.branch_id,
        },
    )
    return {"task_id": task_id, "book_id": book_id, "success": True}
