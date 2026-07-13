from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, Optional
from src.core.container import AppContainer as Container
from src.backend.database.uow import UnitOfWork

router = APIRouter(tags=["metrics"])

@router.get("/api/prompt-metrics")
async def get_prompt_metrics(limit: int = 100):
    """
    プロンプトメトリクスの履歴を取得する
    """
    try:
        async with Container.db().get_session() as session:
            from src.backend.database.repositories.prompt_metrics_repo import PromptMetricsRepository
            repo = PromptMetricsRepository(session)
            metrics = await repo.get_latest_metrics(limit=limit)
            return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt metrics: {str(e)}")

@router.get("/api/prompt-metrics/template/{template_name}")
async def get_prompt_metrics_by_template(template_name: str, limit: int = 50):
    """
    特定のテンプレートのプロンプトメトリクスを取得する
    """
    try:
        async with Container.db().get_session() as session:
            from src.backend.database.repositories.prompt_metrics_repo import PromptMetricsRepository
            repo = PromptMetricsRepository(session)
            metrics = await repo.get_metrics_by_template(template_name=template_name, limit=limit)
            return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt metrics for template {template_name}: {str(e)}")

@router.post("/api/prompt-metrics/save")
async def save_prompt_metrics(request: Dict[str, Any]):
    """
    プロンプトメトリクスを保存する
    """
    try:
        async with UnitOfWork(Container.db()) as uow:
            from src.backend.database.repositories.prompt_metrics_repo import PromptMetricsRepository
            repo = PromptMetricsRepository(uow.session)
            await repo.save_metrics(request)
            await uow.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save prompt metrics: {str(e)}")

@router.delete("/api/prompt-metrics")
async def delete_old_prompt_metrics(days: int = 30):
    """
    古いプロンプトメトリクスを削除する
    """
    try:
        async with UnitOfWork(Container.db()) as uow:
            from src.backend.database.repositories.prompt_metrics_repo import PromptMetricsRepository
            repo = PromptMetricsRepository(uow.session)
            deleted_count = await repo.delete_old_metrics(days=days)
            await uow.commit()
        return {"status": "success", "deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete old prompt metrics: {str(e)}")
