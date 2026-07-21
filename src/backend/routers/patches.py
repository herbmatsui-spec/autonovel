from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Any
import json
from sqlalchemy import select

from config.container import Container
from config.project_context import GlobalConfig
from src.backend.patch_validator import PatchValidator
from src.backend.prompt_version_manager import PromptVersionManager
from src.backend.database.models import PendingPatch, PromptVersion
from src.core.exceptions import NotFoundError, ValidationError
from src.backend.auth import require_api_key

router = APIRouter(prefix="/api/patches", tags=["patches"])

@router.get("/{book_id}/pending")
async def get_pending_patches(book_id: int):
    from src.backend.database.uow import UnitOfWork
    async with UnitOfWork(Container.db()) as uow:
        patches = await uow.misc.get_pending_patches(book_id)
    return patches

@router.post("/{patch_id}/approve")
async def approve_patch(patch_id: int, req: Optional[Any] = None, api_key: str = Depends(require_api_key)):
    from src.backend.database.uow import UnitOfWork
    async with UnitOfWork(Container.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError("Patch not found", resource_type="PendingPatch", resource_id=str(patch_id))

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(patch.patch_content)
            if not validation.is_safe:
                raise ValidationError(f"Config patch validation failed: {', '.join(validation.errors)}")

            # GlobalConfigに即時適用
            for k, v in validation.sanitized_patch.items():
                GlobalConfig().set(k, v)

        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(patch.patch_content)
            if not validation.is_safe:
                raise ValidationError(f"Prompt patch validation failed: {', '.join(validation.errors)}")

            # プロンプトパッチをアクティブ化する
            ver_res = await uow.session.execute(
                select(PromptVersion)
                .where(PromptVersion.book_id == patch.book_id)
                .where(PromptVersion.content == patch.patch_content)
            )
            ver = ver_res.scalar_one_or_none()

            if ver:
                pvm = PromptVersionManager(uow.db)
                await uow.prompt_versions.set_active_prompt_version(
                    book_id=patch.book_id,
                    prompt_key="optimized_prompt_patch",
                    version_id=ver.id
                )

            # GlobalConfigに反映
            GlobalConfig().set("optimized_prompt_patch", patch.patch_content)

        # ステータス更新
        await uow.misc.update_patch_status(patch_id, "approved")

    return {"message": "Patch approved and applied successfully"}

@router.post("/{patch_id}/reject")
async def reject_patch(patch_id: int, req: Optional[Any] = None, api_key: str = Depends(require_api_key)):
    from src.backend.database.uow import UnitOfWork
    async with UnitOfWork(Container.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError("Patch not found", resource_type="PendingPatch", resource_id=str(patch_id))

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        await uow.misc.update_patch_status(patch_id, "rejected")
    return {"message": "Patch rejected successfully"}

@router.post("/{patch_id}/edit")
async def edit_patch(patch_id: int, req: Any, api_key: str = Depends(require_api_key)):
    # Note: PatchEditRequest should be imported from api_schemas in the actual final version
    # For now, we assume it's handled by the request body
    from src.backend.database.uow import UnitOfWork
    async with UnitOfWork(Container.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError("Patch not found", resource_type="PendingPatch", resource_id=str(patch_id))

        if patch.status != "pending":
            raise ValidationError(f"Cannot edit patch in status: {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(req.content)
            if not validation.is_safe:
                raise ValidationError(f"Config patch validation failed: {', '.join(validation.errors)}")
        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(req.content)
            if not validation.is_safe:
                raise ValidationError(f"Prompt patch validation failed: {', '.join(validation.errors)}")

        # パッチ内容を書き換え
        patch.patch_content = req.content
        # バージョン履歴のコンテンツも同期する（プロンプトの場合）
        if patch.patch_type == "prompt":
            ver_res = await uow.session.execute(
                select(PromptVersion)
                .where(PromptVersion.book_id == patch.book_id)
                .where(PromptVersion.ab_test_metrics.like(f'%"pending_patch_id": {patch_id}%'))
            )
            ver = ver_res.scalar_one_or_none()
            if ver:
                ver.content = req.content

    return {"message": "Patch content updated successfully"}
