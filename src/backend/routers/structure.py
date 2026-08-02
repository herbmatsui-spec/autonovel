"""
routers/structure.py - 物語構造テンプレート検証 API

structure_validator を用いて、作品のプロット構造をテンプレートと照合し、
不足ビート・クライマックス位置・ペーシングを検証する。
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query

from src.backend.database.models import Plot
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer as Container
from src.services.structure_validator import list_structures, validate

router = APIRouter(prefix="/api/structure", tags=["structure"])


@router.get("/templates")
async def get_templates() -> List[Dict[str, Any]]:
    """利用可能な構造テンプレート一覧を取得する。"""
    return list_structures()


@router.get("/books/{book_id}/validate")
async def validate_structure(
    book_id: int,
    structure: str = Query("three_act", description="three_act | kishotenketsu | hero_journey"),
) -> Dict[str, Any]:
    """作品のプロット構造を検証する。"""
    from sqlalchemy import select

    async with UnitOfWork(Container.db()) as uow:
        result = await uow.session.execute(
            select(Plot)
            .where(Plot.book_id == book_id)
            .order_by(Plot.ep_num)
        )
        plots = [
            {"ep_num": p.ep_num, "title": p.title, "tension": p.tension or 0}
            for p in result.scalars().all()
        ]

    return validate(plots, structure)
