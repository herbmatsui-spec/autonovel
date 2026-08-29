from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.backend.auth import require_api_key
from src.backend.response_helpers import api_success
from src.backend.router_helpers import workflow_endpoint
from src.core.container import AppContainer
from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.shared.utils import StatusReporter

router = APIRouter(prefix="/api/illustrations", tags=["illustrations"])


def get_illustration_workflow():
    return AppContainer.illustration_workflow()


class GenerateIllustrationSchema(BaseModel):
    book_id: int
    illustration_type: str = "cover"
    episode_number: Optional[int] = None
    character_id: Optional[int] = None
    model: str = "auto"
    enable_r15: bool = False
    aspect_ratio: str = "3:4"
    prompt_override: Optional[str] = None


class BatchIllustrationSchema(BaseModel):
    book_id: int
    settings: Dict[str, Any] = Field(default_factory=dict)


@workflow_endpoint("illustration_generate")
@router.post("/generate")
async def generate_illustration(
    req: GenerateIllustrationSchema,
    workflow=Depends(get_illustration_workflow),
    api_key: str = Depends(require_api_key)
):
    """単一の挿絵を生成する"""
    try:
        ill_request = IllustrationRequest(
            book_id=req.book_id,
            illustration_type=IllustrationType(req.illustration_type),
            episode_number=req.episode_number,
            character_id=req.character_id,
            model=IllustrationModel(req.model),
            safety_level=SafetyLevel.R15_CONTENT if req.enable_r15 else SafetyLevel.BLOCK_SOME,
            aspect_ratio=req.aspect_ratio,
            prompt_override=req.prompt_override,
        )

        _ = StatusReporter(id="api_gen")
        res = await workflow.illustration_agent.run(request=ill_request)

        if isinstance(res, dict) and res.get("status") == "error":
            raise HTTPException(status_code=500, detail=res.get("message", "Illustration generation failed"))

        return api_success(res.get("result", res) if isinstance(res, dict) else res, "挿絵を生成しました")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@workflow_endpoint("illustration_batch")
@router.post("/batch")
async def batch_generate_illustrations(
    req: BatchIllustrationSchema,
    workflow=Depends(get_illustration_workflow),
    api_key: str = Depends(require_api_key)
):
    """バッチで挿絵を生成する"""
    try:
        reporter = StatusReporter(id=f"batch_{req.book_id}")
        res = await workflow.execute(reporter=reporter, book_id=req.book_id, settings=req.settings)
        return api_success(res, "挿絵をバッチ生成しました")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
