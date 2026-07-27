import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse
from src.services.digest_service import generate_suggestions, process_chapter

router = APIRouter()
logger = logging.getLogger(__name__)

async def generate_with_llm(**kwargs: Any) -> Dict[str, Any]:
    """Stub function to satisfy mypy until implementation is clarified."""
    return {"text": "stub response", "time": 0}


@router.post("/generate")
async def generate_content(input_data: EasyModeInput, current_chapter: str) -> GenerationResponse:
    try:
        # 章の中身処理
        processed_chapter = process_chapter(current_chapter)

        # 生成パラメータ準備
        params = {
            "chapter_history": input_data.chapter_history,
            "current_chapter": processed_chapter,
            "character": input_data.character_params
        }

        # 生成実行
        response = await generate_with_llm(**params)

        return GenerationResponse(
            output=response["text"],
            completion_time_ms=response["time"],
            suggestions=generate_suggestions(processed_chapter)
        )
    except ValidationError as e:
        logger.error(f"Validation failed: {e.errors}")
        raise HTTPException(status_code=422, detail=e.errors)
    except TimeoutError:
        logger.error("Generation timeout")
        raise HTTPException(status_code=504, detail="Generation timeout")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/export/{book_id}")
async def export_easy_mode_package(book_id: int):
    """かんたんモードで作成された作品の納品パッケージ (ZIP) をエクスポートする"""
    from fastapi.responses import Response
    from src.services.marketing import MarketingAgent

    agent = MarketingAgent()
    zip_bytes, zip_filename = await agent.create_export_package(book_id)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )

