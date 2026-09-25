from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.errors import retry_on_lock

if TYPE_CHECKING:
    pass

from src.backend.database.core import DatabaseManager
from src.backend.database.models import Outbox
from src.backend.database.outbox import ChromaOutboxService
from src.backend.database.repositories import (
    AuditRepository,
    BibleRepository,
    BookRepository,
    BookScoreRepository,
    BranchRepository,
    ChapterRepository,
    CharacterRepository,
    CollabRepository,
    CostRepository,
    IllustrationRepository,
    MiscRepository,
    NarrativeMetricRepository,
    PDCAHistoryRepository,
    PlotRepository,
    PromptMetricsRepository,
    PromptVersionRepository,
    RulesRepository,
    TraceRepository,
)
from src.backend.database.uow_context import current_uow

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    SQLite のトランザクション整合性と ChromaDB への同期（Outboxパターン）を保証する Unit of Work。
    """

    def __init__(self, db: DatabaseManager | None = None):
        if db is None:
            try:
                from src.core.container import AppContainer
                self.db = AppContainer.db()
            except Exception:
                self.db = None  # type: ignore[assignment]
        else:
            self.db = db
        self.session: AsyncSession | None = None
        self._token = None
        self._repo_cache: dict[type[Any], Any] = {}

        self.outbox_service = ChromaOutboxService()
        self._chroma_additions: list[dict[str, Any]] = []
        self._chroma_deletions: list[dict[str, Any]] = []

    def stage_chroma_add(
        self,
        collection: str,
        doc_id: str,
        doc_content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ):
        """ChromaDBへのドキュメント追加をステージング"""
        self._chroma_additions.append(
            {
                "collection": collection,
                "id": doc_id,
                "content": doc_content,
                "embedding": embedding,
                "metadata": metadata,
            }
        )

    def stage_chroma_delete(self, collection: str, ids: list[str]):
        """ChromaDBからのドキュメント削除をステージング"""
        self._chroma_deletions.append({"collection": collection, "ids": ids})

    def _get_repo(self, repo_cls: type[Any]) -> Any:
        if repo_cls not in self._repo_cache:
            self._repo_cache[repo_cls] = repo_cls(self.session)
        return self._repo_cache[repo_cls]

    @property
    def bible(self) -> BibleRepository:
        return self._get_repo(BibleRepository)

    @property
    def books(self) -> BookRepository:
        return self._get_repo(BookRepository)

    @property
    def branches(self) -> BranchRepository:
        return self._get_repo(BranchRepository)

    @property
    def chapters(self) -> ChapterRepository:
        return self._get_repo(ChapterRepository)

    @property
    def characters(self) -> CharacterRepository:
        return self._get_repo(CharacterRepository)

    @property
    def misc(self) -> MiscRepository:
        return self._get_repo(MiscRepository)

    @property
    def plots(self) -> PlotRepository:
        return self._get_repo(PlotRepository)

    @property
    def rules(self) -> RulesRepository:
        return self._get_repo(RulesRepository)

    @property
    def audit(self) -> AuditRepository:
        return self._get_repo(AuditRepository)

    @property
    def book_scores(self) -> BookScoreRepository:
        return self._get_repo(BookScoreRepository)

    @property
    def prompt_versions(self) -> PromptVersionRepository:
        return self._get_repo(PromptVersionRepository)

    @property
    def prompt_metrics(self) -> PromptMetricsRepository:
        return self._get_repo(PromptMetricsRepository)

    @property
    def pdca_history(self) -> PDCAHistoryRepository:
        return self._get_repo(PDCAHistoryRepository)

    @property
    def illustrations(self) -> IllustrationRepository:
        return self._get_repo(IllustrationRepository)

    @property
    def collab(self) -> CollabRepository:
        return self._get_repo(CollabRepository)

    @property
    def cost(self) -> CostRepository:
        return self._get_repo(CostRepository)

    @property
    def narrative_metrics(self) -> NarrativeMetricRepository:
        return self._get_repo(NarrativeMetricRepository)

    @property
    def trace(self) -> TraceRepository:
        return self._get_repo(TraceRepository)

    async def __aenter__(self) -> UnitOfWork:
        if hasattr(self.db, "get_session"):
            self.session = self.db.get_session()
        elif callable(self.db):
            self.session = self.db()
        else:
            self.session = self.db
        if self.session is None:
            raise RuntimeError("Session not initialized")
        if not self.session.in_transaction():
            await self.session.begin()
        self._token = current_uow.set(self)  # type: ignore
        return self

    async def get_pending_outbox_events(self) -> list[Outbox]:
        """未処理のアウトボックスイベントを取得"""
        from sqlalchemy import select

        if self.session is None:
            raise RuntimeError("Session not initialized")
        result = await self.session.execute(
            select(Outbox).where(Outbox.status == "pending").order_by(Outbox.created_at)
        )
        return list(result.scalars().all())

    async def mark_outbox_event_processed(self, event_id: int) -> None:
        """アウトボックスイベントを処理済みにマーク"""
        import datetime

        from sqlalchemy import update

        if self.session is None:
            raise RuntimeError("Session not initialized")
        await self.session.execute(
            update(Outbox)
            .where(Outbox.id == event_id)
            .values(status="done", processed_at=datetime.datetime.now())
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                logger.warning(f"[UOW] Rolling back SQLite transaction due to exception: {exc_val}")
                if self.session:
                    await self.session.rollback()
            else:
                # コミット前に、ステージングされたChromaDB操作をoutboxに記録
                if self.session is None:
                    raise RuntimeError("Session not initialized")

                async def _commit_with_retry():
                    if self.session:
                        await self.outbox_service.flush(
                            self.session, self._chroma_additions, self._chroma_deletions
                        )
                        await self.session.commit()
                    else:
                        raise RuntimeError("Session is None during commit")

                # retry_on_lock(retries=...)(func) returns the wrapper. We then call the wrapper.
                await retry_on_lock()(_commit_with_retry)()
                logger.info(
                    f"[UOW] SQLite transaction committed with retry. Staged {len(self._chroma_additions)} Chroma adds, {len(self._chroma_deletions)} Chroma deletes to outbox."
                )
        except Exception as e:
            logger.error(f"[UOW] Error finalizing transaction: {e}")
            raise
        finally:
            if self._token:
                current_uow.reset(self._token)
                self._token = None
            if self.session:
                await self.session.close()
            self.session = None
            self._repo_cache.clear()
            self._chroma_additions.clear()
            self._chroma_deletions.clear()
