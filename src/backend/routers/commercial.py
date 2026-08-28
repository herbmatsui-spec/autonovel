"""
src/backend/routers/commercial.py — Commercial Pipeline API
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.backend.auth import require_api_key
from src.backend.response_helpers import api_success
from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.backend.router_helpers import workflow_endpoint
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id
from src.backend.task_helpers import create_task as _create_task

from src.core.exceptions import PipelineError

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
        # タスクIDを生成
        task_id = generate_task_id("commercial")
        # タスクの初期状態をDBに保存
        await _create_task(task_id, "商用化パイプラインを開始中...", total_steps=1)
        # バックグラウンドタスクをエンqueue
        from src.backend.tasks import run_commercial_pipeline_task
        run_commercial_pipeline_task(
            task_id=task_id,
            series_config=config.series_config,
            samples=config.samples,
            platforms=config.platforms,
            api_key=api_key,
        )
        # タスクIDを返却
        return api_success({"task_id": task_id}, "商用化パイプラインを開始しました")
    except Exception as e:
        raise PipelineError(f"Pipeline execution failed: {str(e)}", original=e)