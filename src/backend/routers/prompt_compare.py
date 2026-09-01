"""
routers/prompt_compare.py - ジャンル別プロンプト A/B 比較 API

同一入力（テスト文）に対して複数のプロンプトバージョンで評価し、
品質スコアで比較・勝者を決定する。生成は呼び出し側が用意した texts を渡す形とし、
LLM呼び出しは行わない（低性能環境でも実行可能）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.backend.database.models import PromptVersion
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.services.prompt_comparison import build_comparison

router = APIRouter(prefix="/api/prompt-compare", tags=["prompt-compare"])


class CompareRequest(BaseModel):
    prompt_key: str
    texts: List[str]
    weights: Optional[Dict[str, float]] = None


@router.get("/books/{book_id}/versions")
async def list_versions(book_id: int, prompt_key: str = Query(...)) -> List[Dict[str, Any]]:
    """作品の指定プロンプトキーのバージョン一覧を取得する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        from sqlalchemy import select

        result = await uow.session.execute(
            select(PromptVersion)
            .where(PromptVersion.book_id == book_id)
            .where(PromptVersion.prompt_key == prompt_key)
            .order_by(PromptVersion.id)
        )
        rows = result.scalars().all()
    return [
        {"id": r.id, "version_tag": r.version_tag, "content": r.content, "is_active": r.is_active}
        for r in rows
    ]


@router.post("/books/{book_id}/compare")
async def compare(book_id: int, req: CompareRequest) -> Dict[str, Any]:
    """複数バージョンの出力を比較し、勝者を決定する。"""
    if not req.texts:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="texts は必須です")

    async with UnitOfWork(AppContainer.db()) as uow:
        from sqlalchemy import select

        result = await uow.session.execute(
            select(PromptVersion)
            .where(PromptVersion.book_id == book_id)
            .where(PromptVersion.prompt_key == req.prompt_key)
            .order_by(PromptVersion.id)
        )
        versions = [
            {"id": r.id, "version_tag": r.version_tag, "content": r.content}
            for r in result.scalars().all()
        ]

    # texts の数に合わせてバージョンを切り詰め/補完
    n = min(len(versions), len(req.texts))
    if n == 0:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail="比較対象のプロンプトバージョンが見つかりません"
        )
    versions = versions[:n]
    texts = req.texts[:n]
    return await build_comparison(versions, texts, req.weights)


@router.post("/books/{book_id}/versions/{version_id}/activate")
async def activate_version(book_id: int, version_id: int) -> Dict[str, Any]:
    """指定バージョンをアクティブ（採用）にする。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.prompt_versions.set_active_prompt_version(book_id, "", -1)
        # prompt_key を取得してから正しくセット
        from sqlalchemy import select

        row = (
            await uow.session.execute(select(PromptVersion).where(PromptVersion.id == version_id))
        ).scalar_one_or_none()
        if row is None:
            from src.core.exceptions import NotFoundError

            raise NotFoundError(
                "PromptVersion not found",
                resource_type="PromptVersion",
                resource_id=str(version_id),
            )
        await uow.prompt_versions.set_active_prompt_version(book_id, row.prompt_key, version_id)
    return {"status": "success", "id": version_id}
