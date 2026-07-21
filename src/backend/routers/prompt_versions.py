from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from src.models.api_schemas import RollbackRequest
from config.container import Container
from src.backend.database import UnitOfWork
from config.project_context import GlobalConfig
from src.backend.auth import validate_api_key_or_raise

router = APIRouter(tags=["prompt_versions"])

@router.get("/api/prompt_versions/{book_id}")
async def get_prompt_versions(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        versions = await uow.prompt_versions.get_prompt_versions(book_id)
    return versions

@router.post("/api/prompt_versions/{book_id}/rollback")
async def rollback_prompt_version(book_id: int, req: RollbackRequest):
    validate_api_key_or_raise(req.api_key)
    from src.backend.prompt_version_manager import PromptVersionManager
    pvm = PromptVersionManager(Container.db())

    async with UnitOfWork(Container.db()) as uow:
        # 指定バージョンの検証
        ver = await uow.prompt_versions.get_prompt_version(req.version_id)
        if not ver or ver["book_id"] != book_id:
            from src.core.exceptions import NotFoundError
            raise NotFoundError("Prompt version not found or mismatched book_id", resource_type="PromptVersion", resource_id=str(req.version_id))

        # ロールバック実行
        await uow.prompt_versions.record_rollback(req.version_id, req.reason or "手動ロールバック")

        # 以前のバージョンに戻す (1つ前の健全なバージョン)
        versions = await uow.prompt_versions.get_prompt_versions(book_id, limit=20)
        previous_candidates = [
            v for v in versions
            if v["prompt_key"] == "optimized_prompt_patch"
            and v["id"] != req.version_id
            and not v["rollback_reason"]
        ]

        if previous_candidates:
            fallback_ver = previous_candidates[0]
            await uow.prompt_versions.set_active_prompt_version(book_id, "optimized_prompt_patch", fallback_ver["id"])
            GlobalConfig().set("optimized_prompt_patch", fallback_ver["content"])
            msg = f"Rollback successful. Reverted to version {fallback_ver['version_tag']}"
        else:
            GlobalConfig().set("optimized_prompt_patch", "")
            msg = "Rollback successful. Reverted to default empty prompt (no healthy history found)"

    return {"message": msg}
