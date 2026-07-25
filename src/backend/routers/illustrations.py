from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from fastapi import BackgroundTasks

from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
    IllustrationModel,
    SafetyLevel,
)
from src.services.image_service import ImageService
from src.agents.illustration_agent import IllustrationAgent
from src.backend.workflows.illustration_workflow import IllustrationWorkflow
from src.shared.utils import StatusReporter
import os

router = APIRouter()

# 依存関係の注入用ヘルパー
def get_illustration_workflow():
    api_key = os.getenv("GOOGLE_GENAI_API_KEY", "")
    img_service = ImageService(api_key=api_key)
    ill_agent = IllustrationAgent(image_service=img_service)
    # repoは本来DIコンテナから取得するが、ここでは簡略化してWorkflow内で管理させるか
    # 実際にはserver.pyなどで注入される想定
    return IllustrationWorkflow(illustration_agent=ill_agent)

@router.post("/generate")
async def generate_illustration(
    request: Dict[str, Any], 
    workflow=Depends(get_illustration_workflow)
):
    """単一の挿絵を生成する"""
    try:
        # リクエストのパース
        ill_request = IllustrationRequest(
            book_id=request["book_id"],
            illustration_type=IllustrationType(request["illustration_type"]),
            episode_number=request.get("episode_number"),
            model=IllustrationModel(request.get("model", "quality")),
            safety_level=SafetyLevel.R15_CONTENT if request.get("enable_r15") else SafetyLevel.BLOCK_SOME
        )
        
        # 簡易的なレポート
        reporter = StatusReporter(id="api_gen")
        
        # Agentを直接呼んで生成
        res = await workflow.illustration_agent.run(request=ill_request)
        
        if res["status"] == "error":
            raise HTTPException(status_code=500, detail=res["message"])
            
        return res["result"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch")
async def batch_generate_illustrations(
    params: Dict[str, Any], 
    workflow=Depends(get_illustration_workflow)
):
    """バッチで挿絵を生成する"""
    try:
        book_id = params["book_id"]
        settings = params.get("settings", {})
        
        # 実際にはStatusReporterを通じてフロントエンドに通知するが、
        # API経由の場合は完了まで待つか、タスクIDを返す
        reporter = StatusReporter(id=f"batch_{book_id}")
        
        res = await workflow.execute(
            reporter=reporter,
            book_id=book_id,
            settings=settings
        )
        
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
