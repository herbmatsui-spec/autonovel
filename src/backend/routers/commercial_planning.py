"""
40話ビートシート取得・編集APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.planning import PlanningAgent
from src.backend.auth import get_current_user
from src.backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/commercial/planning",
    tags=["commercial-planning"],
    dependencies=[Depends(get_current_user)],
)

class BeatSheetItem(BaseModel):
    ep_num: int
    phase: str
    mission: str
    tension_target: float
    visual_scene_focus: str

class BeatSheetResponse(BaseModel):
    items: List[BeatSheetItem]

class BeatSheetGenerateRequest(BaseModel):
    title: str
    synopsis: str
    # Optional additional parameters for the agent

@router.get("/{book_id}", response_model=BeatSheetResponse)
async def get_beat_sheet(
    book_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    書籍IDに紐づく40話ビートシートを取得する。
    存在しない場合は404を返す。
    """
    # TODO: 実際にはデータベースからビートシートを取得するロジックを実装
    # ここでは仮の実装として空のリストを返す
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/generate", response_model=BeatSheetResponse)
async def generate_beat_sheet(
    request: BeatSheetGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    タイトルとあらすじから40話ビートシートを生成し、データベースに保存する。
    """
    # TODO: 実際にはPlanningAgentを使ってビートシートを生成し、データベースに保存する
    # ここでは仮の実装として空のリストを返す
    raise HTTPException(status_code=501, detail="Not implemented")