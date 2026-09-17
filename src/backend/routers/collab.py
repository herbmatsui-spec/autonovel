"""
routers/collab.py - 共同執筆・レビューコメント API

メンバー管理・章へのコメント投稿・解決マークを提供する。
コメント更新は SSE でリアルタイム配信する（簡易実装：ポーリング代替）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.backend.auth import get_current_user
from src.backend.database.models import User
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


async def _verify_book_access(uow: UnitOfWork, book_id: int, current_user: User) -> None:
    """リクエストユーザーがブックの所有者または管理者であることを検証する。"""
    book = await uow.books.get_book(book_id)
    if not book:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))

    if current_user.role != "admin" and getattr(book, "user_id", None) is not None:
        if book.user_id != current_user.id:
            # メンバーリストに含まれるかも確認
            members = await uow.collab.list_members(book_id)
            member_names = {m.user_name for m in members}
            if current_user.display_name not in member_names and current_user.email not in member_names:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="この作品へのアクセス権限がありません",
                )


# ---- Members ----
@router.post("/books/{book_id}/members")
async def add_member(
    book_id: int,
    req: MemberRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        await _verify_book_access(uow, book_id, current_user)
        mid = await uow.collab.add_member(book_id, req.user_name, req.role)
    return {"status": "success", "id": mid}


@router.get("/books/{book_id}/members")
async def list_members(
    book_id: int,
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    async with UnitOfWork(AppContainer.db()) as uow:
        await _verify_book_access(uow, book_id, current_user)
        members = await uow.collab.list_members(book_id)
    return [
        {"id": m.id, "user_name": m.user_name, "role": m.role, "invited_at": str(m.invited_at)}
        for m in members
    ]


@router.delete("/books/{book_id}/members/{member_id}")
async def remove_member(
    book_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        await _verify_book_access(uow, book_id, current_user)
        n = await uow.collab.remove_member(member_id)
    if n == 0:
        from src.core.exceptions import NotFoundError

        raise NotFoundError(
            "Member not found", resource_type="ProjectMember", resource_id=str(member_id)
        )
    return {"status": "success", "id": member_id}


# ---- Comments ----
@router.post("/books/{book_id}/chapters/{chapter_ep}/comments")
async def add_comment(
    book_id: int,
    chapter_ep: int,
    req: CommentRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        await _verify_book_access(uow, book_id, current_user)
        cid = await uow.collab.add_comment(
            book_id=book_id,
            chapter_ep=chapter_ep,
            author_name=req.author_name or current_user.display_name or "Anonymous",
            content=req.content,
            anchor_text=req.anchor_text,
            parent_id=req.parent_id,
        )
    return {"status": "success", "id": cid}


@router.get("/books/{book_id}/comments")
async def list_comments(
    book_id: int,
    chapter_ep: int | None = Query(None),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    async with UnitOfWork(AppContainer.db()) as uow:
        await _verify_book_access(uow, book_id, current_user)
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
async def resolve_comment(
    comment_id: int,
    payload: dict[str, Any] = {},
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
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
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with UnitOfWork(AppContainer.db()) as uow:
        n = await uow.collab.delete_comment(comment_id)
    if n == 0:
        from src.core.exceptions import NotFoundError

        raise NotFoundError(
            "Comment not found", resource_type="Comment", resource_id=str(comment_id)
        )
    return {"status": "success", "id": comment_id}
