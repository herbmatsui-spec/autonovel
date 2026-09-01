"""
src/backend/routers/commercial.py — Commercial Pipeline API
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.backend.auth import require_api_key
from src.backend.workflows.commercial_pipeline import CommercialPipeline

router = APIRouter(prefix="/commercial", tags=["commercial"])


class CommercialConfig(BaseModel):
    """商用化パイプライン設定"""

    series_config: dict[str, Any] = {}
    samples: list[dict[str, Any]] = []
    platforms: list[str] = ["kakuyomu", "naru"]  # デフォルトプラットフォーム


@router.post("/run", response_model=dict[str, Any])
async def run_commercial_pipeline(
    config: CommercialConfig, api_key: str = Depends(require_api_key)
):
    """
    Commercial Pipeline を実行するエンドポイント。

    Args:
        config: Commercial Config

    Returns:
        Executed pipeline result
    """
    try:
        # パイプライン実行
        result = CommercialPipeline.run(
            series_config=config.series_config, samples=config.samples, platforms=config.platforms
        )

        # 結果を標準化して返却
        return {"success": True, "data": result, "trace_id": f"comm_{hash(str(config))[:8]}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
