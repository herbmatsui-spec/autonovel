"""
src/backend/routers/collab.py - コラボレーション（メンバー・コメント） API エンドポイント

テスト用に FastAPI ルーターは不要だが、他のコードで利用できるように作成。
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.container import Container
from src.backend.database.uow import UnitOfWork

router = APIRouter(prefix="/api/collab", tags=["collab"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class MemberRequest(BaseModel):
    user_name: str = Field(..., description="メンバー名")
    role: str = Field("viewer", description="ロール (viewer/editor)")

class MemberResponse(BaseModel):
    id: int
    user_name: str
    role: str

class CommentRequest(BaseModel):
    author_name: str = Field(..., description="コメント投稿者")
    content: str = Field(..., description="コメント本文")
    anchor_text: Optional[str] = Field("", description="アンカーテキスト (省略可)")
    parent_id: Optional[int] = Field(None, description="親コメント ID (スレッド)")

# ---------------------------------------------------------------------------
# Helper to acquire a UnitOfWork using the test‑overridden DB (Container.db)
# ---------------------------------------------------------------------------

def _uow() -> UnitOfWork:
    return UnitOfWork(Container.db())

# ---------------------------------------------------------------------------
# API functions – used directly in tests via ``from src.backend.routers import collab as collab_router``
# ---------------------------------------------------------------------------

@router.post("/books/{book_id}/members", response_model=dict)
async def add_member(book_id: int, req: MemberRequest) -> dict:
    async with _uow() as uow:
        member_id = await uow.collab.add_member(book_id, req.user_name, req.role)
    return {"status": "success", "member_id": member_id}

@router.get("/books/{book_id}/members", response_model=List[MemberResponse])
async def list_members(book_id: int) -> List[MemberResponse]:
    async with _uow() as uow:
        members = await uow.collab.list_members(book_id)
    return [MemberResponse(id=m.id, user_name=m.user_name, role=m.role) for m in members]

@router.post("/books/{book_id}/chapters/{chapter_ep}/comments", response_model=dict)
async def add_comment(book_id: int, chapter_ep: int, req: CommentRequest) -> dict:
    async with _uow() as uow:
        comment_id = await uow.collab.add_comment(
            book_id,
            chapter_ep,
            req.author_name,
            req.content,
            anchor_text=req.anchor_text or "",
            parent_id=req.parent_id,
        )
    return {"status": "success", "comment_id": comment_id}

@router.get("/books/{book_id}/comments", response_model=List[dict])
async def list_comments(book_id: int, chapter_ep: Optional[int] = None) -> List[dict]:
    async with _uow() as uow:
        comments = await uow.collab.list_comments(book_id, chapter_ep)
    return [
        {
            "id": c.id,
            "author_name": c.author_name,
            "content": c.content,
            "anchor_text": c.anchor_text,
            "parent_id": c.parent_id,
            "resolved": c.resolved,
        }
        for c in comments
    ]

@router.patch("/comments/{comment_id}", response_model=dict)
async def resolve_comment(comment_id: int, payload: dict) -> dict:
    resolved = payload.get("resolved", True)
    async with _uow() as uow:
        await uow.collab.resolve_comment(comment_id, resolved)
    return {"resolved": resolved}

# The router object is exported for FastAPI inclusion, but the tests call the
# functions directly (e.g. ``await collab_router.add_member(...)``).
