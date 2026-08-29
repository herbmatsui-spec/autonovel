from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
import os

from src.backend.auth import require_api_key
from src.backend.database.models import PendingPatch, PromptVersion
from src.backend.patch_validator import PatchValidator
from src.backend.prompt_version_manager import PromptVersionManager
from src.backend.response_helpers import api_success
from src.backend.router_helpers import workflow_endpoint
from src.core.container import AppContainer
from src.core.exceptions import NotFoundError, ValidationError
from src.models.api_schemas import PatchEditRequest
from config.settings import ConfigManager

router = APIRouter(prefix="/api/patches", tags=["patches"])


@router.get("/{book_id}/pending")
async def get_pending_patches(book_id: int):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        patches = await uow.misc.get_pending_patches(book_id)
    return patches


@workflow_endpoint("patch_approve")
@router.post("/{patch_id}/approve")
async def approve_patch(
    patch_id: int, req: Optional[Any] = None, api_key: str = Depends(require_api_key)
):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(patch.patch_content)
            if not validation.is_safe:
                raise ValidationError(
                    f"Config patch validation failed: {', '.join(validation.errors)}"
                )

            # GlobalConfigに即時適用
            for k, v in validation.sanitized_patch.items():
                os.environ[f"KAKU_{k.upper()}"] = str(v)
                ConfigManager.clear_cache()

        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(patch.patch_content)
            if not validation.is_safe:
                raise ValidationError(
                    f"Prompt patch validation failed: {', '.join(validation.errors)}"
                )

            # プロンプトパッチをアクティブ化する
            ver_res = await uow.session.execute(
                select(PromptVersion)
                .where(PromptVersion.book_id == patch.book_id)
                .where(PromptVersion.content == patch.patch_content)
            )
            ver = ver_res.scalar_one_or_none()

            if ver:
                PromptVersionManager(uow.db)
                await uow.prompt_versions.set_active_prompt_version(
                    book_id=patch.book_id, prompt_key="optimized_prompt_patch", version_id=ver.id
                )

            # 環境変数経由で反映
            os.environ["KAKU_OPTIMIZED_PROMPT_PATCH"] = patch.patch_content
            ConfigManager.clear_cache()

        # ステータス更新
        await uow.misc.update_patch_status(patch_id, "approved")

    return api_success({"message": "Patch approved and applied successfully"}, "パッチを適用しました")


@workflow_endpoint("patch_reject")
@router.post("/{patch_id}/reject")
async def reject_patch(
    patch_id: int, req: Optional[Any] = None, api_key: str = Depends(require_api_key)
):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        await uow.misc.update_patch_status(patch_id, "rejected")
    return api_success({"message": "Patch rejected successfully"}, "パッチを拒否しました")


@workflow_endpoint("patch_edit")
@router.post("/{patch_id}/edit")
async def edit_patch(patch_id: int, req: PatchEditRequest, api_key: str = Depends(require_api_key)):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        if patch.status != "pending":
            raise ValidationError(f"Cannot edit patch in status: {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(req.content)
            if not validation.is_safe:
                raise ValidationError(
                    f"Config patch validation failed: {', '.join(validation.errors)}"
                )
        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(req.content)
            if not validation.is_safe:
                raise ValidationError(
                    f"Prompt patch validation failed: {', '.join(validation.errors)}"
                )

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

    return api_success({"message": "Patch content updated successfully"}, "パッチを更新しました")
