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
    BranchRepository,
    ChapterRepository,
    CharacterRepository,
    IllustrationRepository,
    MiscRepository,
    PlotRepository,
    PromptMetricsRepository,
    PromptVersionRepository,
    RulesRepository,
)
from src.backend.database.uow_context import current_uow

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    SQLite のトランザクション整合性と ChromaDB への同期（Outboxパターン）を保証する Unit of Work。
    """

    @inject
    def __init__(self, db: DatabaseManager = Provide["db"]):
        self.db = db
        self.session: AsyncSession | None = None
        self._token = None
        self._bible: BibleRepository | None = None
        self._books: BookRepository | None = None
        self._branches: BranchRepository | None = None
        self._chapters: ChapterRepository | None = None
        self._characters: CharacterRepository | None = None
        self._misc: MiscRepository | None = None
        self._plots: PlotRepository | None = None
        self._rules: RulesRepository | None = None
        self._audit: AuditRepository | None = None
        self._prompt_versions: PromptVersionRepository | None = None
        self._prompt_metrics: PromptMetricsRepository | None = None
        self._illustrations: IllustrationRepository | None = None

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

    @property
    def bible(self) -> BibleRepository:
        if self._bible is None:
            self._bible = BibleRepository(self.session)
        return self._bible

    @property
    def books(self) -> BookRepository:
        if self._books is None:
            self._books = BookRepository(self.session)
        return self._books

    @property
    def branches(self) -> BranchRepository:
        if self._branches is None:
            self._branches = BranchRepository(self.session)
        return self._branches

    @property
    def chapters(self) -> ChapterRepository:
        if self._chapters is None:
            self._chapters = ChapterRepository(self.session)
        return self._chapters

    @property
    def characters(self) -> CharacterRepository:
        if self._characters is None:
            self._characters = CharacterRepository(self.session)
        return self._characters

    @property
    def misc(self) -> MiscRepository:
        if self._misc is None:
            self._misc = MiscRepository(self.session)
        return self._misc

    @property
    def plots(self) -> PlotRepository:
        if self._plots is None:
            self._plots = PlotRepository(self.session)
        return self._plots

    @property
    def rules(self) -> RulesRepository:
        if self._rules is None:
            self._rules = RulesRepository(self.session)
        return self._rules

    @property
    def audit(self) -> AuditRepository:
        if self._audit is None:
            self._audit = AuditRepository(self.session)
        return self._audit

    @property
    def prompt_versions(self) -> PromptVersionRepository:
        if self._prompt_versions is None:
            self._prompt_versions = PromptVersionRepository(self.session)
        return self._prompt_versions

    @property
    def prompt_metrics(self) -> PromptMetricsRepository:
        if self._prompt_metrics is None:
            self._prompt_metrics = PromptMetricsRepository(self.session)
        return self._prompt_metrics

    @property
    def illustrations(self) -> IllustrationRepository:
        if self._illustrations is None:
            self._illustrations = IllustrationRepository(self.session)
        return self._illustrations

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.db.get_session()
        if self.session is None:
            raise RuntimeError("Session not initialized")
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
            self._bible = None
            self._books = None
            self._branches = None
            self._chapters = None
            self._characters = None
            self._misc = None
            self._plots = None
            self._rules = None
            self._audit = None
            self._prompt_versions = None
            self._prompt_metrics = None
            self._chroma_additions.clear()
            self._chroma_deletions.clear()
