"""Web小説投稿サイト向けワンクリック整形テキスト出力ルーター (v5.0 Step 12).

「なろう」「カクヨム」「アルファポリス」等の各プラットフォーム規格に
最適化されたテキスト（字下げ・ルビ記法・前書き/後書き）を返却する。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter

router = APIRouter(prefix="/api/export/copy", tags=["export-copy"])


class CopyFormatRequest(BaseModel):
    """整形リクエスト。"""

    title: str
    body: str
    foreword: str = ""
    afterword: str = ""
    platform: str = "narou"  # "narou", "kakuyomu", "alphapolis"


class CopyFormatResponse(BaseModel):
    """整形レスポンス。"""

    title: str
    foreword: str
    body: str
    afterword: str
    total_characters: int
    platform: str


@router.post("/", response_model=CopyFormatResponse)
async def format_chapter_for_copy(req: CopyFormatRequest) -> CopyFormatResponse:
    """Web小説投稿サイト別の整形済みテキストを返却する（クリップボードコピー用）。"""
    res = PlatformCopyFormatter.format_for_platform(
        title=req.title,
        body=req.body,
        foreword=req.foreword,
        afterword=req.afterword,
        platform=req.platform,
    )
    return CopyFormatResponse(
        title=res.title,
        foreword=res.foreword,
        body=res.body,
        afterword=res.afterword,
        total_characters=res.total_characters,
        platform=res.platform,
    )
