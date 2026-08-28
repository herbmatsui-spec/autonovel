"""
src/services/branch_service.py - ブランチ分岐管理サービス
"""

from __future__ import annotations

import logging
from typing import Optional

from src.backend.database.core import DatabaseManager
from src.backend.database.repositories.branch import BranchRepository
from src.schemas.ux_schemas import BranchCreateRequest, BranchCreateResponse
from src.shared.domain_event_bus import DomainEvent, get_domain_event_bus

logger = logging.getLogger(__name__)


class BranchService:
    """小説のIFルートやマルチエンディング分岐を管理するサービス"""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        branch_repo: Optional[BranchRepository] = None,
    ) -> None:
        self.db_manager = db_manager
        self.branch_repo = branch_repo
        self.event_bus = get_domain_event_bus()

    async def create_fork(self, req: BranchCreateRequest) -> BranchCreateResponse:
        """What-If スニペットや指定話数から新しいブランチ（分岐）を作成する"""
        logger.info(
            f"[BranchService] Forking branch for book_id={req.book_id}, "
            f"parent_id={req.parent_branch_id}, fork_ep={req.fork_ep_num}, name='{req.new_name}'"
        )

        branch_id: int = 1

        if self.branch_repo is not None:
            branch_id = await self.branch_repo.create_branch(
                book_id=req.book_id,
                name=req.new_name,
                parent_id=req.parent_branch_id,
                fork_ep_num=req.fork_ep_num,
                divergence_reason=req.divergence_reason or "",
                what_if_snippet=req.what_if_snippet,
            )
        elif self.db_manager is not None:
            async with self.db_manager.get_session() as session:
                repo = BranchRepository(session)
                branch_id = await repo.create_branch(
                    book_id=req.book_id,
                    name=req.new_name,
                    parent_id=req.parent_branch_id,
                    fork_ep_num=req.fork_ep_num,
                    divergence_reason=req.divergence_reason or "",
                    what_if_snippet=req.what_if_snippet,
                )
                await session.commit()
        else:
            # フォールバック / モック用
            import random
            branch_id = random.randint(100, 999)

        # イベントバスへ発行
        await self.event_bus.publish(
            "BRANCH_FORKED",
            DomainEvent(
                type="BRANCH_FORKED",
                book_id=req.book_id,
                ep=req.fork_ep_num,
                payload={
                    "branch_id": branch_id,
                    "parent_id": req.parent_branch_id,
                    "name": req.new_name,
                    "divergence_reason": req.divergence_reason or "",
                },
            ),
        )

        return BranchCreateResponse(
            branch_id=branch_id,
            book_id=req.book_id,
            name=req.new_name,
            parent_id=req.parent_branch_id,
            fork_ep_num=req.fork_ep_num,
            divergence_reason=req.divergence_reason or "",
            status="created",
        )
