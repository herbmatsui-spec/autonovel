"""EasyModeDraft リポジトリ — Gacha Pitch / Quick Digest / Review Session の永続化."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select

from src.backend.database.models import EasyModeDraft
from src.backend.database.repositories.base import BaseRepository
from src.domain.entities.review_session import ReviewSession
from src.services.errors import retry_on_lock

logger = logging.getLogger("easy_mode_draft_repo")


class EasyModeDraftRepository(BaseRepository[EasyModeDraft]):
    """EasyModeDraft テーブルへの CRUD 操作を提供する。"""

    model_class = EasyModeDraft

    @retry_on_lock()
    async def save_gacha_plans(self, request_id: str, plans_json: dict) -> None:
        """GachaService.generate_plans() の出力を保存する。

        Args:
            request_id: GachaPitch の request_id（draft_id として使用）
            plans_json: GachaResponse.model_dump() でシリアライズした dict
        """
        draft = EasyModeDraft(
            draft_id=request_id,
            kind="gacha",
            payload_json=json.dumps(plans_json, ensure_ascii=False),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.session.add(draft)
        logger.debug("[easy-mode-draft-repo] Saved gacha plans: request_id=%s", request_id)

    async def load_gacha_plans(self, request_id: str) -> dict | None:
        """request_id に対応する GachaPitch のoplan を読み込む。

        Returns:
            plans_json: GachaResponse.model_dump() 相当の dict。
            存在しない場合は None。
        """
        result = await self.session.execute(
            select(EasyModeDraft).where(
                EasyModeDraft.draft_id == request_id,
                EasyModeDraft.kind == "gacha",
            )
        )
        draft = result.scalar_one_or_none()
        if draft is None:
            return None
        try:
            return json.loads(draft.payload_json)
        except json.JSONDecodeError:
            logger.warning(
                "[easy-mode-draft-repo] Failed to parse payload_json for draft_id=%s",
                request_id,
            )
            return None

    @retry_on_lock()
    async def save_digest(self, book_id: str, parent_request_id: str, digest_json: dict) -> None:
        """DigestService.generate_digest() の出力を保存する。

        Args:
            book_id: 生成されたブック ID（draft_id として使用）
            parent_request_id: 対応する GachaPitch の request_id
            digest_json: DigestResponse.model_dump() でシリアライズした dict
        """
        draft = EasyModeDraft(
            draft_id=book_id,
            kind="digest",
            payload_json=json.dumps(digest_json, ensure_ascii=False),
            parent_draft_id=parent_request_id,
            book_id=book_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.session.add(draft)
        logger.debug(
            "[easy-mode-draft-repo] Saved digest: book_id=%s, parent_request_id=%s",
            book_id,
            parent_request_id,
        )

    async def load_digest(self, book_id: str) -> dict | None:
        """book_id に対応する Quick Digest の成果物を読み込む。

        Returns:
            digest_json: DigestResponse.model_dump() 相当の dict。
            存在しない場合は None。
        """
        result = await self.session.execute(
            select(EasyModeDraft).where(
                EasyModeDraft.draft_id == book_id,
                EasyModeDraft.kind == "digest",
            )
        )
        draft = result.scalar_one_or_none()
        if draft is None:
            return None
        try:
            return json.loads(draft.payload_json)
        except json.JSONDecodeError:
            logger.warning(
                "[easy-mode-draft-repo] Failed to parse payload_json for book_id=%s",
                book_id,
            )
            return None

    async def load_parent_gacha(self, book_id: str) -> dict | None:
        """book_id に対応する Digest の親 GachaPitch を読み込む。

        Returns:
            plans_json: 親 GachaPitch の plans dict。
            存在しない場合は None。
        """
        result = await self.session.execute(
            select(EasyModeDraft).where(
                EasyModeDraft.draft_id == book_id,
                EasyModeDraft.kind == "digest",
            )
        )
        digest_draft = result.scalar_one_or_none()
        if digest_draft is None or digest_draft.parent_draft_id is None:
            return None
        return await self.load_gacha_plans(digest_draft.parent_draft_id)

    # --- Review Session Methods ---

    @retry_on_lock()
    async def save_review_session(self, session: ReviewSession) -> None:
        """ReviewSession を永続化。

        Args:
            session: 保存する ReviewSession インスタンス
        """
        draft = EasyModeDraft(
            draft_id=session.session_id,
            kind="review_session",
            payload_json=json.dumps(session.to_dict(), ensure_ascii=False),
            review_session_json=json.dumps(session.to_dict(), ensure_ascii=False),
            parent_draft_id=session.request_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        self.session.add(draft)
        logger.debug(
            "[easy-mode-draft-repo] Saved review session: session_id=%s, request_id=%s",
            session.session_id,
            session.request_id,
        )

    async def load_review_session(self, session_id: str) -> ReviewSession | None:
        """session_id で ReviewSession を読み込み。

        Returns:
            ReviewSession インスタンス。存在しない場合は None。
        """
        result = await self.session.execute(
            select(EasyModeDraft).where(
                EasyModeDraft.draft_id == session_id,
                EasyModeDraft.kind == "review_session",
            )
        )
        draft = result.scalar_one_or_none()
        if draft is None:
            return None
        try:
            data = json.loads(draft.review_session_json or draft.payload_json)
            return ReviewSession.from_dict(data)
        except json.JSONDecodeError:
            logger.warning(
                "[easy-mode-draft-repo] Failed to parse review_session_json for session_id=%s",
                session_id,
            )
            return None

    async def load_review_session_by_request(self, request_id: str) -> ReviewSession | None:
        """request_id から最新の ReviewSession を読み込み。

        Returns:
            最新の ReviewSession インスタンス。存在しない場合は None。
        """
        result = await self.session.execute(
            select(EasyModeDraft).where(
                EasyModeDraft.parent_draft_id == request_id,
                EasyModeDraft.kind == "review_session",
            ).order_by(EasyModeDraft.created_at.desc())
        )
        draft = result.scalars().first()
        if draft is None:
            return None
        try:
            data = json.loads(draft.review_session_json or draft.payload_json)
            return ReviewSession.from_dict(data)
        except json.JSONDecodeError:
            logger.warning(
                "[easy-mode-draft-repo] Failed to parse review_session_json for request_id=%s",
                request_id,
            )
            return None
