"""Novel Publishing Platform Export and Preview Endpoints (Steps 61, 62)."""

from __future__ import annotations

import io
import urllib.parse
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.services.formatters.ruby_transpiler import PublishPlatform
from src.services.formatters.platform_formatter import PlatformFormatter
from src.backend.database.series_loader import SeriesDataLoader, SeriesDataLoaderConfig

router = APIRouter(prefix="/publish", tags=["publishing"])


class PublishExportRequest(BaseModel):
    book_id: int
    branch_id: Optional[int] = None


@router.post("/{platform}")
async def export_for_publishing(
    platform: PublishPlatform,
    req: PublishExportRequest,
):
    """Export formatted novel package as a ZIP archive for the specified platform (Step 61)."""
    loader = SeriesDataLoader()
    try:
        config = SeriesDataLoaderConfig(
            book_id=req.book_id,
            branch_id=req.branch_id,
            fallback_to_minimal=True,
        )
        series = loader.load_series(config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to load book data: {e}"
        )

    episodes_data = [
        {
            "title": ep.title,
            "content": ep.content,
            "foreword": ep.metadata.get("foreword", ""),
            "afterword": ep.metadata.get("afterword", ""),
        }
        for ep in series.episodes
    ]

    zip_bytes = PlatformFormatter.package_for_platform(
        title=series.title or f"Book_{req.book_id}",
        synopsis=series.synopsis or "",
        episodes=episodes_data,
        platform=platform,
    )

    filename = f"{series.title or 'novel'}_{platform.value}.zip"
    encoded_filename = urllib.parse.quote(filename)

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/{platform}/preview")
async def preview_for_publishing(
    platform: PublishPlatform,
    book_id: int = Query(..., description="Target Book ID"),
    chapter_number: int = Query(1, description="Episode/Chapter number to preview"),
    branch_id: Optional[int] = Query(None, description="Optional branch ID"),
):
    """Preview formatted episode text and check platform limit warnings (Step 62)."""
    loader = SeriesDataLoader()
    try:
        config = SeriesDataLoaderConfig(
            book_id=book_id,
            branch_id=branch_id,
            fallback_to_minimal=True,
        )
        series = loader.load_series(config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to load book data: {e}"
        )

    # Find requested episode
    ep = None
    for item in series.episodes:
        if item.episode_num == chapter_number:
            ep = item
            break
    if not ep and series.episodes:
        ep = series.episodes[0]

    if not ep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_number} not found"
        )

    formatted = PlatformFormatter.format_episode_with_author_notes(
        title=ep.title,
        content=ep.content,
        platform=platform,
        foreword=ep.metadata.get("foreword", ""),
        afterword=ep.metadata.get("afterword", ""),
    )

    warnings = PlatformFormatter.validate_limits(
        title=series.title or "",
        synopsis=series.synopsis or "",
        platform=platform,
    )

    return {
        "book_id": book_id,
        "platform": platform.value,
        "chapter_number": ep.episode_num,
        "title": ep.title,
        "formatted_content": formatted["full_text"],
        "content_body_only": formatted["content"],
        "foreword": formatted["foreword"],
        "afterword": formatted["afterword"],
        "warnings": warnings,
    }
