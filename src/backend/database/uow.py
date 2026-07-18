from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession

from services.errors import retry_on_lock

from config.container import Container
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
    def __init__(self, db: DatabaseManager = Provide[Container.db]):
        self.db = db
        self.session: Optional[AsyncSession] = None
        self._token = None
        self._bible: Optional[BibleRepository] = None
        self._books: Optional[BookRepository] = None
        self._branches: Optional[BranchRepository] = None
        self._chapters: Optional[ChapterRepository] = None
        self._characters: Optional[CharacterRepository] = None
        self._misc: Optional[MiscRepository] = None
        self._plots: Optional[PlotRepository] = None
        self._rules: Optional[RulesRepository] = None
        self._audit: Optional[AuditRepository] = None
        self._prompt_versions: Optional[PromptVersionRepository] = None
        self._prompt_metrics: Optional[PromptMetricsRepository] = None

        self.outbox_service = ChromaOutboxService()
        self._chroma_additions: List[Dict[str, Any]] = []
        self._chroma_deletions: List[Dict[str, Any]] = []

    def stage_chroma_add(self, collection: str, doc_id: str, doc_content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        """ChromaDBへのドキュメント追加をステージング"""
        self._chroma_additions.append({
            "collection": collection,
            "id": doc_id,
            "content": doc_content,
            "embedding": embedding,
            "metadata": metadata
        })

    def stage_chroma_delete(self, collection: str, ids: List[str]):
        """ChromaDBからのドキュメント削除をステージング"""
        self._chroma_deletions.append({
            "collection": collection,
            "ids": ids
        })

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

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.db.get_session()
        if self.session is None:
            raise RuntimeError("Session not initialized")
        await self.session.begin()
        self._token = current_uow.set(self) # type: ignore
        return self

    async def get_pending_outbox_events(self) -> List[Outbox]:
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
                    await self.outbox_service.flush(self.session, self._chroma_additions, self._chroma_deletions)
                    await self.session.commit()

                # retry_on_lock(retries=...)(func) returns the wrapper. We then call the wrapper.
                await retry_on_lock()( _commit_with_retry)()
                logger.info(f"[UOW] SQLite transaction committed with retry. Staged {len(self._chroma_additions)} Chroma adds, {len(self._chroma_deletions)} Chroma deletes to outbox.")
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
