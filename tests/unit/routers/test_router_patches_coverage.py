"""Patches router coverage: approve/reject/edit/review/setting-versions/paragraph flows."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import src.backend.routers.patches as patches_module
from src.backend.routers.patches import (
    ParagraphPatchRequest,
    ReviewActionRequest,
    ReviseReviewRequest,
    approve_patch,
    approve_review,
    edit_patch,
    get_pending_patches,
    get_pending_reviews,
    get_review_detail,
    get_setting_version,
    get_setting_versions,
    patch_paragraph,
    reject_patch,
    reject_review,
    revise_review,
)
from src.core.exceptions import NotFoundError, ValidationError


def make_uow(session=None, misc=None, db=None):
    """UnitOfWork を模倣する async context manager。"""
    uow = MagicMock()
    uow.session = session if session is not None else MagicMock()
    uow.misc = misc if misc is not None else MagicMock()
    uow.db = db if db is not None else MagicMock()

    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


def make_patch(patch_id=1, book_id=10, status="pending", patch_type="config",
               content="{}"):
    return SimpleNamespace(id=patch_id, book_id=book_id, status=status,
                           patch_type=patch_type, patch_content=content)


@pytest.fixture(autouse=True)
def patch_uow_and_ownership(monkeypatch):
    """UnitOfWork / AppContainer.db / verify_book_ownership を差し替える。

    関数内で ``from src.backend.database.uow import UnitOfWork`` が再importされるため、
    ソースモジュール側もパッチする。fixture は ``uow`` 属性を持つオブジェクトを返す。
    """
    uow = make_uow()
    import src.backend.database.uow as uow_source
    monkeypatch.setattr(patches_module, "UnitOfWork", lambda db=None: uow)
    monkeypatch.setattr(uow_source, "UnitOfWork", lambda db=None: uow)
    monkeypatch.setattr(patches_module.AppContainer, "db", lambda: None)
    monkeypatch.setattr(patches_module, "verify_book_ownership", AsyncMock())
    # 関数内 import される所有権確認も差し替え
    import src.backend.security.owner_guard as owner_guard_source
    monkeypatch.setattr(owner_guard_source, "verify_book_ownership", AsyncMock())
    return SimpleNamespace(uow=uow)


# ============================================================================
# get_pending_patches / get_pending_reviews
# ============================================================================


@pytest.mark.asyncio
async def test_get_pending_patches(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    patches = [{"id": 1}, {"id": 2}]
    uow.misc.get_pending_patches = AsyncMock(return_value=patches)
    user = MagicMock()
    result = await get_pending_patches(10, current_user=user)
    assert result == patches
    uow.misc.get_pending_patches.assert_awaited_once_with(10)
    patches_module.verify_book_ownership.assert_awaited_once()


# ============================================================================
# approve_patch
# ============================================================================


@pytest.mark.asyncio
async def test_approve_patch_no_session_raises(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    uow.session = None
    with pytest.raises(RuntimeError, match="Database session not initialized"):
        await approve_patch(1, None, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_patch_not_found(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    uow.session.execute = AsyncMock(return_value=result)
    from src.core.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await approve_patch(999, None, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_patch_already_processed(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(status="approved")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)
    from src.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="already approved"):
        await approve_patch(1, None, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_patch_config_safe_applies_globalconfig(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="config", content='{"key": "value"}')
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)
    uow.misc.update_patch_status = AsyncMock()

    validation = SimpleNamespace(is_safe=True, sanitized_patch={"key": "value"}, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_config_patch",
                        lambda content: validation)
    set_calls = []
    monkeypatch.setattr(patches_module.GlobalConfig,
                        "set", lambda self, k, v: set_calls.append((k, v)))

    result_msg = await approve_patch(1, None, current_user=MagicMock())
    assert result_msg == {"message": "Patch approved and applied successfully"}
    assert set_calls == [("key", "value")]
    uow.misc.update_patch_status.assert_awaited_once_with(1, "approved")


@pytest.mark.asyncio
async def test_approve_patch_config_unsafe_raises(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="config", content="bad")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)

    validation = SimpleNamespace(is_safe=False, sanitized_patch=None,
                                 errors=["dangerous key"])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_config_patch",
                        lambda content: validation)
    from src.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="dangerous key"):
        await approve_patch(1, None, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_patch_config_safe_but_no_sanitized(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="config", content="{}")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)

    validation = SimpleNamespace(is_safe=True, sanitized_patch=None, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_config_patch",
                        lambda content: validation)
    from src.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="Sanitized patch is missing"):
        await approve_patch(1, None, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_patch_prompt_with_version(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="prompt", content="new prompt", book_id=10)
    patch_result = MagicMock()
    patch_result.scalar_one_or_none.return_value = patch
    ver = SimpleNamespace(id=77)
    ver_result = MagicMock()
    ver_result.scalar_one_or_none.return_value = ver

    uow.session.execute = AsyncMock(side_effect=[patch_result, ver_result])
    uow.misc.update_patch_status = AsyncMock()
    uow.prompt_versions.set_active_prompt_version = AsyncMock()

    validation = SimpleNamespace(is_safe=True, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_prompt_patch",
                        lambda content: validation)
    set_calls = []
    monkeypatch.setattr(patches_module.GlobalConfig,
                        "set", lambda self, k, v: set_calls.append((k, v)))

    result_msg = await approve_patch(1, None, current_user=MagicMock())
    assert result_msg == {"message": "Patch approved and applied successfully"}
    uow.prompt_versions.set_active_prompt_version.assert_awaited_once_with(
        book_id=10, prompt_key="optimized_prompt_patch", version_id=77
    )
    assert set_calls == [("optimized_prompt_patch", "new prompt")]


@pytest.mark.asyncio
async def test_approve_patch_prompt_without_version(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="prompt", content="new prompt", book_id=10)
    patch_result = MagicMock()
    patch_result.scalar_one_or_none.return_value = patch
    ver_result = MagicMock()
    ver_result.scalar_one_or_none.return_value = None

    uow.session.execute = AsyncMock(side_effect=[patch_result, ver_result])
    uow.misc.update_patch_status = AsyncMock()

    validation = SimpleNamespace(is_safe=True, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_prompt_patch",
                        lambda content: validation)
    set_calls = []
    monkeypatch.setattr(patches_module.GlobalConfig,
                        "set", lambda self, k, v: set_calls.append((k, v)))

    result_msg = await approve_patch(1, None, current_user=MagicMock())
    assert result_msg == {"message": "Patch approved and applied successfully"}
    assert set_calls == [("optimized_prompt_patch", "new prompt")]
    # set_active_prompt_version は呼ばれない（uow.prompt_versions は MagicMock だが）
    uow.misc.update_patch_status.assert_awaited_once_with(1, "approved")


# ============================================================================
# reject_patch
# ============================================================================


@pytest.mark.asyncio
async def test_reject_patch_success(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(status="pending")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)
    uow.misc.update_patch_status = AsyncMock()

    result_msg = await reject_patch(1, None, current_user=MagicMock())
    assert result_msg == {"message": "Patch rejected successfully"}
    uow.misc.update_patch_status.assert_awaited_once_with(1, "rejected")


@pytest.mark.asyncio
async def test_reject_patch_not_found_and_already_processed(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    uow.session.execute = AsyncMock(return_value=result)
    from src.core.exceptions import NotFoundError, ValidationError
    with pytest.raises(NotFoundError):
        await reject_patch(999, None, current_user=MagicMock())

    patch = make_patch(status="approved")
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result2)
    with pytest.raises(ValidationError, match="already approved"):
        await reject_patch(1, None, current_user=MagicMock())


# ============================================================================
# edit_patch
# ============================================================================


@pytest.mark.asyncio
async def test_edit_patch_config(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="config", content="{}")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)

    validation = SimpleNamespace(is_safe=True, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_config_patch",
                        lambda content: validation)
    req = SimpleNamespace(content='{"new": "value"}')

    result_msg = await edit_patch(1, req, current_user=MagicMock())
    assert result_msg == {"message": "Patch content updated successfully"}
    assert patch.patch_content == '{"new": "value"}'


@pytest.mark.asyncio
async def test_edit_patch_prompt_syncs_version(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="prompt", content="old", book_id=10)
    patch_result = MagicMock()
    patch_result.scalar_one_or_none.return_value = patch
    ver = SimpleNamespace(id=5, content="old")
    ver_result = MagicMock()
    ver_result.scalar_one_or_none.return_value = ver

    uow.session.execute = AsyncMock(side_effect=[patch_result, ver_result])

    validation = SimpleNamespace(is_safe=True, errors=[])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_prompt_patch",
                        lambda content: validation)
    req = SimpleNamespace(content="new")

    result_msg = await edit_patch(1, req, current_user=MagicMock())
    assert result_msg == {"message": "Patch content updated successfully"}
    assert patch.patch_content == "new"
    assert ver.content == "new"


@pytest.mark.asyncio
async def test_edit_patch_unsafe_and_errors(patch_uow_and_ownership, monkeypatch):
    uow = patch_uow_and_ownership.uow
    patch = make_patch(patch_type="prompt", content="old")
    result = MagicMock()
    result.scalar_one_or_none.return_value = patch
    uow.session.execute = AsyncMock(return_value=result)

    validation = SimpleNamespace(is_safe=False, errors=["invalid"])
    monkeypatch.setattr(patches_module.PatchValidator, "validate_prompt_patch",
                        lambda content: validation)
    req = SimpleNamespace(content="new")
    from src.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="invalid"):
        await edit_patch(1, req, current_user=MagicMock())

    # not pending -> error
    patch2 = make_patch(status="rejected", patch_type="config", content="{}")
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = patch2
    uow.session.execute = AsyncMock(return_value=result2)
    req2 = SimpleNamespace(content="{}")
    with pytest.raises(ValidationError, match="Cannot edit patch"):
        await edit_patch(1, req2, current_user=MagicMock())


# ============================================================================
# Reviews
# ============================================================================


@pytest.mark.asyncio
async def test_get_pending_reviews(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    reviews = [{"id": 3}]
    uow.misc.get_pending_reviews = AsyncMock(return_value=reviews)
    result = await get_pending_reviews(10, current_user=MagicMock())
    assert result == reviews
    patches_module.verify_book_ownership.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_review_detail(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    result = await get_review_detail(3, current_user=MagicMock())
    assert result == review
    patches_module.verify_book_ownership.assert_awaited_once_with(10, patches_module.verify_book_ownership.call_args[0][1], patches_module.verify_book_ownership.call_args[0][2])


@pytest.mark.asyncio
async def test_get_review_detail_not_found(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    uow.misc.get_patch_review = AsyncMock(return_value=None)
    from src.core.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await get_review_detail(999, current_user=MagicMock())


@pytest.mark.asyncio
async def test_approve_review_with_audit_issues(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10, "status": "under_review",
              "audit_issue_ids": [1, 2]}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    uow.misc.update_patch_review_status = AsyncMock()
    uow.session.execute = AsyncMock()

    req = ReviewActionRequest(reviewer_id="user1", comment="ok")
    result_msg = await approve_review(3, req, current_user=MagicMock())
    assert result_msg == {"message": "Review approved successfully"}
    uow.misc.update_patch_review_status.assert_awaited_once_with(
        3, "approved", reviewer_id="user1", review_comment="ok"
    )
    uow.session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_review_without_audit_issues(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10, "status": "under_review", "audit_issue_ids": []}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    uow.misc.update_patch_review_status = AsyncMock()

    result_msg = await approve_review(3, ReviewActionRequest(), current_user=MagicMock())
    assert result_msg == {"message": "Review approved successfully"}
    uow.session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_approve_review_errors(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    uow.misc.get_patch_review = AsyncMock(return_value=None)
    from src.core.exceptions import NotFoundError, ValidationError
    with pytest.raises(NotFoundError):
        await approve_review(999, ReviewActionRequest(), current_user=MagicMock())

    review = {"id": 3, "book_id": 10, "status": "approved", "audit_issue_ids": []}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    with pytest.raises(ValidationError, match="already approved"):
        await approve_review(3, ReviewActionRequest(), current_user=MagicMock())


@pytest.mark.asyncio
async def test_reject_review_requires_comment(patch_uow_and_ownership):
    with pytest.raises(ValidationError, match="Comment is required"):
        await reject_review(3, ReviewActionRequest(comment=""), current_user=MagicMock())
    # comment がある場合はそのまま通る
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10, "status": "under_review", "audit_issue_ids": []}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    uow.misc.update_patch_review_status = AsyncMock()
    result_msg = await reject_review(3, ReviewActionRequest(comment="reason"),
                                     current_user=MagicMock())
    assert result_msg == {"message": "Review rejected successfully"}


@pytest.mark.asyncio
async def test_reject_review_success(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10, "status": "under_review",
              "audit_issue_ids": [1]}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    uow.misc.update_patch_review_status = AsyncMock()
    uow.session.execute = AsyncMock()

    req = ReviewActionRequest(reviewer_id="user1", comment="no good")
    result_msg = await reject_review(3, req, current_user=MagicMock())
    assert result_msg == {"message": "Review rejected successfully"}
    uow.misc.update_patch_review_status.assert_awaited_once_with(
        3, "rejected", reviewer_id="user1", review_comment="no good"
    )
    uow.session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_review_success(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    review = {"id": 3, "book_id": 10, "status": "under_review"}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    uow.session.execute = AsyncMock()

    req = ReviseReviewRequest(proposed_content="better text", reviewer_id="u1",
                              comment="fix")
    result_msg = await revise_review(3, req, current_user=MagicMock())
    assert result_msg == {"message": "Review revised successfully, awaiting re-approval"}
    uow.session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_review_errors(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    uow.misc.get_patch_review = AsyncMock(return_value=None)
    from src.core.exceptions import NotFoundError, ValidationError
    with pytest.raises(NotFoundError):
        await revise_review(999, ReviseReviewRequest(proposed_content="x"),
                            current_user=MagicMock())

    review = {"id": 3, "book_id": 10, "status": "approved"}
    uow.misc.get_patch_review = AsyncMock(return_value=review)
    with pytest.raises(ValidationError, match="Cannot revise review"):
        await revise_review(3, ReviseReviewRequest(proposed_content="x"),
                            current_user=MagicMock())


# ============================================================================
# Setting versions
# ============================================================================


@pytest.mark.asyncio
async def test_get_setting_versions(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    versions = [{"version": 1}, {"version": 2}]
    uow.misc.get_setting_versions = AsyncMock(return_value=versions)
    result = await get_setting_versions(10, current_user=MagicMock())
    assert result == versions


@pytest.mark.asyncio
async def test_get_setting_version_found_and_missing(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    version = {"version": 1, "data": {}}
    uow.misc.get_setting_version = AsyncMock(return_value=version)
    result = await get_setting_version(10, 1, current_user=MagicMock())
    assert result == version

    uow.misc.get_setting_version = AsyncMock(return_value=None)
    from src.core.exceptions import NotFoundError
    with pytest.raises(NotFoundError, match="Setting version not found"):
        await get_setting_version(10, 999, current_user=MagicMock())


# ============================================================================
# Paragraph patch
# ============================================================================


@pytest.mark.asyncio
async def test_patch_paragraph_negative_index():
    req = ParagraphPatchRequest(paragraph_index=-1, directive="d")
    with pytest.raises(HTTPException) as exc:
        await patch_paragraph(5, req, current_user=MagicMock())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_patch_paragraph_success(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    chapter = SimpleNamespace(id=5, book_id=10)
    result = MagicMock()
    result.scalar_one_or_none.return_value = chapter
    uow.session.execute = AsyncMock(return_value=result)

    req = ParagraphPatchRequest(paragraph_index=2, directive="more vivid")
    response = await patch_paragraph(5, req, current_user=MagicMock())
    assert response.index == 2
    assert "original content of paragraph 2" in response.original_paragraph
    assert "more vivid" in response.patched_paragraph
    patches_module.verify_book_ownership.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_paragraph_chapter_not_found(patch_uow_and_ownership):
    uow = patch_uow_and_ownership.uow
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    uow.session.execute = AsyncMock(return_value=result)
    from src.core.exceptions import NotFoundError
    req = ParagraphPatchRequest(paragraph_index=0, directive="d")
    with pytest.raises(NotFoundError, match="Episode not found"):
        await patch_paragraph(999, req, current_user=MagicMock())
