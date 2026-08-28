"""
src/backend/routers/commercial.py — Commercial Pipeline API
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.backend.auth import require_api_key
from src.backend.response_helpers import api_success
from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.backend.router_helpers import workflow_endpoint
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id

router = APIRouter(prefix="/commercial", tags=["commercial"])


class CommercialConfig(BaseModel):
    """商用化パイプライン設定"""

    series_config: Dict[str, Any] = {}
    samples: List[Dict[str, Any]] = []
    platforms: List[str] = ["kakuyomu", "naru"]  # デフォルトプラットフォーム


@workflow_endpoint("commercial_publish")
@router.post("/run")
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
        return api_success(result, "商用パイプラインを実行しました")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
