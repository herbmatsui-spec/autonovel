"""IFルートマージ確定コミットサービス (Part 5: Step 50-54)。"""

from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Chapter
from src.backend.database.repositories.branch import BranchRepository
from src.backend.schemas.branch import BranchMergeCommitRequest, BranchMergeCommitResponse

logger = logging.getLogger(__name__)


class BranchMergeService:
    """ブランチ間の競合解決テキストを確定反映し、MERGEノードを永続化するサービスクラス。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _validate_merge_payload(self, request: BranchMergeCommitRequest) -> None:
        """不正な章番号や空テキスト送信の事前バリデーション (Step 54)。"""
        if request.source_branch_id <= 0:
            raise ValueError(f"Invalid source_branch_id: {request.source_branch_id}")
        if request.target_branch_id <= 0:
            raise ValueError(f"Invalid target_branch_id: {request.target_branch_id}")
        if request.source_branch_id == request.target_branch_id:
            raise ValueError("Cannot merge a branch into itself")
        if not request.resolved_chapters:
            raise ValueError("No resolved chapters provided in merge commit payload")

        for chap in request.resolved_chapters:
            if chap.chapter_number <= 0:
                raise ValueError(f"Invalid chapter_number: {chap.chapter_number}")
            if not chap.resolved_content or not chap.resolved_content.strip():
                raise ValueError(f"Resolved content for chapter {chap.chapter_number} cannot be empty")

    async def commit_merge(
        self,
        book_id: int,
        request: BranchMergeCommitRequest,
    ) -> BranchMergeCommitResponse:
        """アトミックトランザクションによる章コンテンツ確定更新とIFグラフMERGEノード反映 (Step 51, 52, 53)。"""
        self._validate_merge_payload(request)

        branch_repo = BranchRepository(self.session)
        source_branch = await branch_repo.get_branch(request.source_branch_id)
        target_branch = await branch_repo.get_branch(request.target_branch_id)

        if not source_branch or not target_branch:
            raise ValueError(f"Source branch {request.source_branch_id} or target branch {request.target_branch_id} not found")

        try:
            # 1. 解決済み各章の確定更新 (Step 51)
            updated_count = 0
            for rc in request.resolved_chapters:
                stmt = select(Chapter).where(
                    Chapter.book_id == book_id,
                    Chapter.branch_id == request.target_branch_id,
                    Chapter.ep_num == rc.chapter_number,
                )
                res = await self.session.execute(stmt)
                chapter = res.scalar_one_or_none()

                if chapter:
                    chapter.content = rc.resolved_content
                else:
                    # ターゲットブランチに章が存在しない場合は新規作成
                    chapter = Chapter(
                        book_id=book_id,
                        branch_id=request.target_branch_id,
                        ep_num=rc.chapter_number,
                        title=f"第{rc.chapter_number}章",
                        content=rc.resolved_content,
                        score_story=80,
                    )
                    self.session.add(chapter)
                updated_count += 1

            # 2. IF グラフ（BranchGraph）への MERGE ノード確定反映 (Step 52)
            target_graph = await branch_repo.load_branch_graph(request.target_branch_id) or {}
            target_graph.setdefault("nodes", {})
            merge_node_id = f"merge_ep{request.merge_ep_num}"
            target_graph["nodes"][merge_node_id] = {
                "id": merge_node_id,
                "episode_num": request.merge_ep_num,
                "content": request.commit_message,
                "branch_type": "merge",
                "resolution_strategies": {
                    str(rc.chapter_number): rc.resolution_strategy for rc in request.resolved_chapters
                },
                "source_branch_id": request.source_branch_id,
                "target_branch_id": request.target_branch_id,
                "committed_at": datetime.utcnow().isoformat(),
            }
            await branch_repo.save_branch_graph(request.target_branch_id, target_graph)

            # 3. マージ履歴（リビジョンログ）の保存 (Step 53)
            logger.info(
                "Successfully committed merge: source=%d -> target=%d, updated_chapters=%d, msg='%s'",
                request.source_branch_id,
                request.target_branch_id,
                updated_count,
                request.commit_message,
            )

            await self.session.commit()

            return BranchMergeCommitResponse(
                success=True,
                target_branch_id=request.target_branch_id,
                updated_chapters_count=updated_count,
                committed_at=datetime.utcnow().isoformat(),
            )
        except Exception as exc:
            await self.session.rollback()
            logger.error("Merge commit failed, rolled back: %s", exc)
            raise
