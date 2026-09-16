from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from config.project_context import GlobalConfig
from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.backend.security.owner_guard import verify_book_ownership
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.backend.database.models import PatchReview, PendingPatch, PromptVersion
from src.backend.patch_validator import PatchValidator
from src.backend.prompt_version_manager import PromptVersionManager
from src.core.exceptions import NotFoundError, ValidationError

# New imports for paragraph patching

router = APIRouter(prefix="/api", tags=["patches"])


class ReviewActionRequest(BaseModel):
    reviewer_id: str | None = None
    comment: str = ""


class ReviseReviewRequest(BaseModel):
    proposed_content: str
    reviewer_id: str | None = None
    comment: str = ""


# New request model for paragraph patching
class ParagraphPatchRequest(BaseModel):
    paragraph_index: int
    directive: str


# New response model for paragraph patching
class ParagraphPatchResponse(BaseModel):
    index: int
    original_paragraph: str
    patched_paragraph: str


@router.get("/patches/{book_id}/pending", dependencies=[Depends(get_current_user)])
async def get_pending_patches(book_id: int, current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        patches = await uow.misc.get_pending_patches(book_id)
    return patches


@router.post("/patches/{patch_id}/approve", dependencies=[Depends(get_current_user)])
async def approve_patch(
    patch_id: int, req: Any | None = None, current_user: User = Depends(get_current_user)
):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        # 所有権を確認
        await verify_book_ownership(patch.book_id, current_user, uow)

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(str(patch.patch_content))
            if not validation.is_safe:
                raise ValidationError(
                    f"Config patch validation failed: {', '.join(validation.errors)}"
                )

            # GlobalConfigに即時適用
            if validation.sanitized_patch is None:
                raise ValidationError("Sanitized patch is missing despite being safe")
            for k, v in validation.sanitized_patch.items():
                GlobalConfig().set(k, v)

        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(str(patch.patch_content))
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


@router.post("/patches/{patch_id}/reject", dependencies=[Depends(get_current_user)])
async def reject_patch(
    patch_id: int, req: Any | None = None, current_user: User = Depends(get_current_user)
):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        # 所有権を確認
        await verify_book_ownership(patch.book_id, current_user, uow)

        if patch.status != "pending":
            raise ValidationError(f"Patch is already {patch.status}")

        await uow.misc.update_patch_status(patch_id, "rejected")
    return {"message": "Patch rejected successfully"}


@router.post("/patches/{patch_id}/edit", dependencies=[Depends(get_current_user)])
async def edit_patch(patch_id: int, req: Any, current_user: User = Depends(get_current_user)):
    # Note: PatchEditRequest should be imported from api_schemas in the actual final version
    # For now, we assume it's handled by the request body
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 該当パッチの取得
        result = await uow.session.execute(select(PendingPatch).where(PendingPatch.id == patch_id))
        patch = result.scalar_one_or_none()
        if not patch:
            raise NotFoundError(
                "Patch not found", resource_type="PendingPatch", resource_id=str(patch_id)
            )

        # 所有権を確認
        await verify_book_ownership(patch.book_id, current_user, uow)

        if patch.status != "pending":
            raise ValidationError(f"Cannot edit patch in status: {patch.status}")

        # 検証
        if patch.patch_type == "config":
            validation = PatchValidator.validate_config_patch(str(req.content))
            if not validation.is_safe:
                raise ValidationError(
                    f"Config patch validation failed: {', '.join(validation.errors)}"
                )
        elif patch.patch_type == "prompt":
            validation = PatchValidator.validate_prompt_patch(str(req.content))
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


@router.get("/patches/{book_id}/reviews", dependencies=[Depends(get_current_user)])
async def get_pending_reviews(book_id: int, current_user: User = Depends(get_current_user)):
    """レビュー待ちパッチ一覧を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 所有権を確認
        await verify_book_ownership(book_id, current_user, uow)
        reviews = await uow.misc.get_pending_reviews(book_id)
    return reviews


@router.get("/patches/reviews/{review_id}", dependencies=[Depends(get_current_user)])
async def get_review_detail(review_id: int, current_user: User = Depends(get_current_user)):
    """レビュー詳細を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        # 所有権を確認 (reviewからbook_idを取得して確認)
        await verify_book_ownership(review["book_id"], current_user, uow)
    return review


@router.post("/patches/reviews/{review_id}/approve", dependencies=[Depends(get_current_user)])
async def approve_review(
    review_id: int, req: ReviewActionRequest, current_user: User = Depends(get_current_user)
):
    """レビューを承認"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        # 所有権を確認
        await verify_book_ownership(review["book_id"], current_user, uow)

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


@router.post("/patches/reviews/{review_id}/reject", dependencies=[Depends(get_current_user)])
async def reject_review(
    review_id: int, req: ReviewActionRequest, current_user: User = Depends(get_current_user)
):
    """レビューを差し戻し"""
    from src.backend.database.uow import UnitOfWork

    if not req.comment:
        raise ValidationError("Comment is required when rejecting a review")

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        # 所有権を確認
        await verify_book_ownership(review["book_id"], current_user, uow)

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
                .values(status="rejected", resolved_note=f"Rejected via review {review_id}: {req.comment}")
            )

    return {"message": "Review rejected successfully"}


@router.post("/patches/reviews/{review_id}/revise", dependencies=[Depends(get_current_user)])
async def revise_review(
    review_id: int, req: ReviseReviewRequest, current_user: User = Depends(get_current_user)
):
    """レビューに修正案を提示（再レビュー要求）"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        # 所有権を確認
        await verify_book_ownership(review["book_id"], current_user, uow)

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


@router.get("/patches/{book_id}/setting-versions", dependencies=[Depends(get_current_user)])
async def get_setting_versions(book_id: int, current_user: User = Depends(get_current_user)):
    """設定バージョン履歴を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 所有権を確認
        await verify_book_ownership(book_id, current_user, uow)
        versions = await uow.misc.get_setting_versions(book_id)
    return versions


@router.get("/patches/{book_id}/setting-versions/{version_number}", dependencies=[Depends(get_current_user)])
async def get_setting_version(book_id: int, version_number: int, current_user: User = Depends(get_current_user)):
    """特定バージョンの設定を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # 所有権を確認
        await verify_book_ownership(book_id, current_user, uow)
        version = await uow.misc.get_setting_version(book_id, version_number)
    if not version:
        raise NotFoundError(
            "Setting version not found",
            resource_type="SettingVersion",
            resource_id=str(version_number),
        )
    return version


# ============================================================================
# Paragraph Patch Endpoint (Manual Paragraph Rewriting)
# ============================================================================


@router.post("/episodes/{episode_id}/patch-paragraph", dependencies=[Depends(get_current_user)])
async def patch_paragraph(
    episode_id: int, req: ParagraphPatchRequest, current_user: User = Depends(get_current_user)
):
    """手動で特定段落のリライトを指示し、即時差分を取得"""
    from src.backend.database.uow import UnitOfWork
    from src.backend.database.models import Chapter
    from sqlalchemy import select
    from src.core.exceptions import NotFoundError

    # Validate paragraph index
    if req.paragraph_index < 0:
        raise HTTPException(status_code=400, detail="Paragraph index must be non-negative")

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")

        # episode_id から chapter を取得し book_id を特定
        result = await uow.session.execute(
            select(Chapter).where(Chapter.id == episode_id)
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise NotFoundError("Episode not found", resource_type="Chapter", resource_id=str(episode_id))

        book_id = chapter.book_id

        # 所有権を確認
        await verify_book_ownership(book_id, current_user, uow)

    # TODO: 実際のパッチロジック実装
    # 現状はダミー実装を維持
    dummy_original = f"This is the original content of paragraph {req.paragraph_index} for episode {episode_id}."
    dummy_patched = f"This is the patched content of paragraph {req.paragraph_index} for episode {episode_id} based on directive: {req.directive}"

    return ParagraphPatchResponse(
        index=req.paragraph_index,
        original_paragraph=dummy_original,
        patched_paragraph=dummy_patched,
    )
