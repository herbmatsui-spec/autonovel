import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.shared.utils import StatusReporter

router = APIRouter()


def get_illustration_workflow():
    container = AppContainer(api_key=os.getenv("GOOGLE_GENAI_API_KEY", ""))
    return container.illustration_workflow()


@router.post("/generate")
async def generate_illustration(
    request: Dict[str, Any], workflow=Depends(get_illustration_workflow)
):
    """単一の挿絵を生成する"""
    try:
        # リクエストのパース
        ill_request = IllustrationRequest(
            book_id=request["book_id"],
            illustration_type=IllustrationType(request["illustration_type"]),
            episode_number=request.get("episode_number"),
            model=IllustrationModel(request.get("model", "auto")),
            safety_level=SafetyLevel.R15_CONTENT
            if request.get("enable_r15")
            else SafetyLevel.BLOCK_SOME,
        )

        # 簡易的なレポート
        _ = StatusReporter(id="api_gen")

        # Agentを直接呼んで生成
        res = await workflow.illustration_agent.run(request=ill_request)

        if res["status"] == "error":
            raise HTTPException(status_code=500, detail=res["message"])

        return res["result"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def batch_generate_illustrations(
    params: Dict[str, Any], workflow=Depends(get_illustration_workflow)
):
    """バッチで挿絵を生成する"""
    try:
        book_id = params["book_id"]
        settings = params.get("settings", {})

        # 実際にはStatusReporterを通じてフロントエンドに通知するが、
        # API経由の場合は完了まで待つか、タスクIDを返す
        reporter = StatusReporter(id=f"batch_{book_id}")

        res = await workflow.execute(reporter=reporter, book_id=book_id, settings=settings)

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
