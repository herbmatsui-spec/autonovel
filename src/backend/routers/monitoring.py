import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.backend.response_helpers import api_success

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class ForeshadowingRow(BaseModel):
    id: int
    book_id: int
    ep_num: int
    type: str
    description: str
    location: Optional[str] = None
    payoff_ep: Optional[int] = None
    fulfilled: bool


class ForeshadowingListResponse(BaseModel):
    total: int
    unresolved: List[ForeshadowingRow]
    resolved: List[ForeshadowingRow]


@router.get("/{book_id}/foreshadowing")
async def get_foreshadowing_list(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        rows = await uow.session.execute(
            "SELECT id, book_id, ep_num, type, description, location, payoff_ep, fulfilled "
            "FROM foreshadowing WHERE book_id = :book_id ORDER BY ep_num",
            {"book_id": book_id}
        )
        all_rows = rows.fetchall()

    unresolved = []
    resolved = []
    for r in all_rows:
        row = ForeshadowingRow(
            id=r.id, book_id=r.book_id, ep_num=r.ep_num,
            type=r.type, description=r.description,
            location=r.location, payoff_ep=r.payoff_ep,
            fulfilled=r.fulfilled
        )
        if r.fulfilled:
            resolved.append(row)
        else:
            unresolved.append(row)

    return api_success({
        "total": len(all_rows),
        "unresolved": [m.model_dump() for m in unresolved],
        "resolved": [m.model_dump() for m in resolved],
    }, "伏線一覧を取得しました")


class CharacterArcRow(BaseModel):
    id: int
    character_id: int
    character_name: str
    arc_name: str
    current_stage_index: int
    total_stages: int
    is_completed: bool


class GrowthPlanListResponse(BaseModel):
    total: int
    arcs: List[CharacterArcRow]


@router.get("/{book_id}/growth")
async def get_growth_plan(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        rows = await uow.session.execute(
            """SELECT ca.id, ca.character_id, c.name as character_name,
                      ca.arc_name, ca.current_stage_index, ca.is_completed,
                      json_array_length(ca.arc_stages) as total_stages
               FROM character_arcs ca
               JOIN characters c ON c.id = ca.character_id
               WHERE ca.book_id = :book_id""",
            {"book_id": book_id}
        )
        all_rows = rows.fetchall()

    arcs = []
    for r in all_rows:
        arcs.append(CharacterArcRow(
            id=r.id,
            character_id=r.character_id,
            character_name=r.character_name,
            arc_name=r.arc_name,
            current_stage_index=r.current_stage_index,
            total_stages=r.total_stages or 1,
            is_completed=r.is_completed
        ))

    return api_success({
        "total": len(arcs),
        "arcs": [a.model_dump() for a in arcs],
    }, "成長フェーズ一覧を取得しました")


class MemoryBoundaryResponse(BaseModel):
    short_term_window: int
    short_term_ep_count: int
    mid_term_arc_size: int
    latest_ep_num: int
    message: str


@router.get("/{book_id}/memory-boundary")
async def get_memory_boundary(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        max_ep_row = await uow.session.execute(
            "SELECT MAX(ep_num) as latest_ep FROM chapters WHERE book_id = :book_id",
            {"book_id": book_id}
        )
        max_ep = max_ep_row.scalar() or 0

    short_term_window = 8  # 短期メモリ窓（固定値）
    mid_term_arc_size = 4  # 中期アークサイズ（固定値）

    async with UnitOfWork(AppContainer.db()) as uow:
        count_row = await uow.session.execute(
            "SELECT COUNT(*) FROM chapters "
            "WHERE book_id = :book_id AND ep_num > :threshold",
            {"book_id": book_id, "threshold": max_ep - short_term_window}
        )
        short_term_count = count_row.scalar() or 0

    return api_success(MemoryBoundaryResponse(
        short_term_window=short_term_window,
        short_term_ep_count=short_term_count,
        mid_term_arc_size=mid_term_arc_size,
        latest_ep_num=max_ep,
        message=f"直近{short_term_window}話中{short_term_count}話が短期メモリに存在"
    ).model_dump(), "メモリ境界を取得しました")


class ConsistencyIssue(BaseModel):
    issue_type: str
    description: str
    ep_num: Optional[int] = None
    related_ep: Optional[int] = None


class ConsistencyCheckResponse(BaseModel):
    issues_found: int
    issues: List[ConsistencyIssue]


@router.get("/{book_id}/consistency")
async def check_consistency(book_id: int):
    issues = []

    async with UnitOfWork(AppContainer.db()) as uow:
        # 伏線解決漏れチェック
        rows = await uow.session.execute(
            """SELECT id, ep_num, description, payoff_ep
               FROM foreshadowing
               WHERE book_id = :book_id
                 AND payoff_ep IS NOT NULL
                 AND payoff_ep <= ep_num
                 AND fulfilled = 0""",
            {"book_id": book_id}
        )
        for r in rows:
            issues.append(ConsistencyIssue(
                issue_type="foreshadowing_unresolved",
                description=f"解決チャプター（{r.payoff_ep}）が導入（{r.ep_num}）以前",
                ep_num=r.ep_num,
                related_ep=r.payoff_ep
            ))

    return api_success(ConsistencyCheckResponse(
        issues_found=len(issues),
        issues=issues
    ).model_dump(), "整合性チェックが完了しました")