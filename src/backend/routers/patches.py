from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from config.project_context import GlobalConfig
from src.backend.auth import require_api_key
from src.backend.database.models import PatchReview, PendingPatch, PromptVersion
from src.backend.patch_validator import PatchValidator
from src.backend.prompt_version_manager import PromptVersionManager
from src.core.container import AppContainer
from src.core.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/api/patches", tags=["patches"])


class ReviewActionRequest(BaseModel):
    reviewer_id: str | None = None
    comment: str = ""


class ReviseReviewRequest(BaseModel):
    proposed_content: str
    reviewer_id: str | None = None
    comment: str = ""


@router.get("/{book_id}/pending")
async def get_pending_patches(book_id: int):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        patches = await uow.misc.get_pending_patches(book_id)
    return patches


@router.post("/{patch_id}/approve")
async def approve_patch(
    patch_id: int, req: Any | None = None, api_key: str = Depends(require_api_key)
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
                GlobalConfig().set(k, v)

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
                _ = PromptVersionManager(uow.db)
                await uow.prompt_versions.set_active_prompt_version(
                    book_id=patch.book_id, prompt_key="optimized_prompt_patch", version_id=ver.id
                )

            # GlobalConfigに反映
            GlobalConfig().set("optimized_prompt_patch", patch.patch_content)

        # ステータス更新
        await uow.misc.update_patch_status(patch_id, "approved")

    return {"message": "Patch approved and applied successfully"}


@router.post("/{patch_id}/reject")
async def reject_patch(
    patch_id: int, req: Any | None = None, api_key: str = Depends(require_api_key)
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
    return {"message": "Patch rejected successfully"}


@router.post("/{patch_id}/edit")
async def edit_patch(patch_id: int, req: Any, api_key: str = Depends(require_api_key)):
    # Note: PatchEditRequest should be imported from api_schemas in the actual final version
    # For now, we assume it's handled by the request body
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

    return {"message": "Patch content updated successfully"}


# ============================================================================
# Patch Review Endpoints (Human-in-the-Loop Review Workflow)
# ============================================================================


@router.get("/{book_id}/reviews")
async def get_pending_reviews(book_id: int):
    """レビュー待ちパッチ一覧を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        reviews = await uow.misc.get_pending_reviews(book_id)
    return reviews


@router.get("/reviews/{review_id}")
async def get_review_detail(review_id: int):
    """レビュー詳細を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        review = await uow.misc.get_patch_review(review_id)
    if not review:
        raise NotFoundError(
            "Review not found", resource_type="PatchReview", resource_id=str(review_id)
        )
    return review


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    review_id: int, req: ReviewActionRequest, api_key: str = Depends(require_api_key)
):
    """レビューを承認"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        if review.get("status") != "under_review":
            raise ValidationError(f"Review is already {review.get('status')}")

        await uow.misc.update_patch_review_status(
            review_id, "approved", reviewer_id=req.reviewer_id, review_comment=req.comment
        )

        # 関連する AuditIssue のステータスも更新
        from sqlalchemy import update
        from src.backend.database.models import AuditIssue

        audit_issue_ids = review.get("audit_issue_ids", [])
        if audit_issue_ids:
            await uow.session.execute(
                update(AuditIssue)
                .where(AuditIssue.id.in_(audit_issue_ids))
                .values(status="resolved", resolved_note=f"Approved via review {review_id}")
            )

    return {"message": "Review approved successfully"}


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    review_id: int, req: ReviewActionRequest, api_key: str = Depends(require_api_key)
):
    """レビューを差し戻し"""
    if not req.comment:
        raise ValidationError("Comment is required when rejecting a review")

    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        if review.get("status") != "under_review":
            raise ValidationError(f"Review is already {review.get('status')}")

        await uow.misc.update_patch_review_status(
            review_id, "rejected", reviewer_id=req.reviewer_id, review_comment=req.comment
        )

        # 関連する AuditIssue のステータスも更新
        from sqlalchemy import update
        from src.backend.database.models import AuditIssue

        audit_issue_ids = review.get("audit_issue_ids", [])
        if audit_issue_ids:
            await uow.session.execute(
                update(AuditIssue)
                .where(AuditIssue.id.in_(audit_issue_ids))
                .values(
                    status="rejected",
                    resolved_note=f"Rejected via review {review_id}: {req.comment}",
                )
            )

    return {"message": "Review rejected successfully"}


@router.post("/reviews/{review_id}/revise")
async def revise_review(
    review_id: int, req: ReviseReviewRequest, api_key: str = Depends(require_api_key)
):
    """レビューに修正案を提示（再レビュー要求）"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        if review.get("status") not in ("under_review", "rejected"):
            raise ValidationError(f"Cannot revise review in status: {review.get('status')}")

        # 提案内容を更新
        from sqlalchemy import update

        await uow.session.execute(
            update(PatchReview)
            .where(PatchReview.id == review_id)
            .values(
                proposed_content=req.proposed_content,
                status="under_review",
                review_comment=req.comment,
                reviewer_id=req.reviewer_id,
            )
        )

    return {"message": "Review revised successfully, awaiting re-approval"}


# ============================================================================
# Setting Version Endpoints
# ============================================================================


@router.get("/{book_id}/setting-versions")
async def get_setting_versions(book_id: int):
    """設定バージョン履歴を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        versions = await uow.misc.get_setting_versions(book_id)
    return versions


@router.get("/{book_id}/setting-versions/{version_number}")
async def get_setting_version(book_id: int, version_number: int):
    """特定バージョンの設定を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        version = await uow.misc.get_setting_version(book_id, version_number)
    if not version:
        raise NotFoundError(
            "Setting version not found",
            resource_type="SettingVersion",
            resource_id=str(version_number),
        )
    return version
