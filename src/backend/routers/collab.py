"""
routers/collab.py - 共同執筆・レビューコメント API

メンバー管理・章へのコメント投稿・解決マークを提供する。
コメント更新は SSE でリアルタイム配信する（簡易実装：ポーリング代替）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer

router = APIRouter(prefix="/api/collab", tags=["collab"])


class MemberRequest(BaseModel):
    user_name: str
    role: str = "viewer"  # owner | editor | viewer


class CommentRequest(BaseModel):
    author_name: str
    content: str
    anchor_text: str = ""
    parent_id: int | None = None


# ---- Members ----
@router.post("/books/{book_id}/members")
async def add_member(book_id: int, req: MemberRequest) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        mid = await uow.collab.add_member(book_id, req.user_name, req.role)
    return {"status": "success", "id": mid}


@router.get("/books/{book_id}/members")
async def list_members(book_id: int) -> list[dict[str, Any]]:
    async with UnitOfWork(AppContainer.db()) as uow:
        members = await uow.collab.list_members(book_id)
    return [
        {"id": m.id, "user_name": m.user_name, "role": m.role, "invited_at": str(m.invited_at)}
        for m in members
    ]


@router.delete("/books/{book_id}/members/{member_id}")
async def remove_member(book_id: int, member_id: int) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        n = await uow.collab.remove_member(member_id)
    if n == 0:
        from src.core.exceptions import NotFoundError

        raise NotFoundError(
            "Member not found", resource_type="ProjectMember", resource_id=str(member_id)
        )
    return {"status": "success", "id": member_id}


# ---- Comments ----
@router.post("/books/{book_id}/chapters/{chapter_ep}/comments")
async def add_comment(book_id: int, chapter_ep: int, req: CommentRequest) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        cid = await uow.collab.add_comment(
            book_id=book_id,
            chapter_ep=chapter_ep,
            author_name=req.author_name,
            content=req.content,
            anchor_text=req.anchor_text,
            parent_id=req.parent_id,
        )
    return {"status": "success", "id": cid}


@router.get("/books/{book_id}/comments")
async def list_comments(
    book_id: int, chapter_ep: int | None = Query(None)
) -> list[dict[str, Any]]:
    async with UnitOfWork(AppContainer.db()) as uow:
        comments = await uow.collab.list_comments(book_id, chapter_ep)
    return [
        {
            "id": c.id,
            "chapter_ep": c.chapter_ep,
            "anchor_text": c.anchor_text,
            "author_name": c.author_name,
            "content": c.content,
            "resolved": c.resolved,
            "parent_id": c.parent_id,
            "created_at": str(c.created_at),
        }
        for c in comments
    ]


@router.patch("/comments/{comment_id}/resolve")
async def resolve_comment(comment_id: int, payload: dict[str, Any] = {}) -> dict[str, Any]:
    resolved = bool(payload.get("resolved", True))
    async with UnitOfWork(AppContainer.db()) as uow:
        n = await uow.collab.resolve_comment(comment_id, resolved)
    if n == 0:
        from src.core.exceptions import NotFoundError

        raise NotFoundError(
            "Comment not found", resource_type="Comment", resource_id=str(comment_id)
        )
    return {"status": "success", "id": comment_id, "resolved": resolved}


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: int) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        n = await uow.collab.delete_comment(comment_id)
    if n == 0:
        from src.core.exceptions import NotFoundError

        raise NotFoundError(
            "Comment not found", resource_type="Comment", resource_id=str(comment_id)
        )
    return {"status": "success", "id": comment_id}
