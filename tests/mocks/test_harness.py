import asyncio
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

from tests.mocks.mock_llm import MockGeminiApiClient
from tests.mocks.mock_repo import (
    MockBookRepository,
    MockPlotRepository,
    MockChapterRepository,
    MockBibleRepository,
    MockBranchRepository,
)

class MockUnitOfWork:
    """
    Integration Mock for UnitOfWork.
    Provides an in-memory state that persists across the UOW lifespan 
    if the repositories are shared, or resets if not.
    """
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.session = AsyncMock()
        
        # Repositories are shared across UOW instances for integration testing
        self._books = MockBookRepository()
        self._plots = MockPlotRepository()
        self._chapters = MockChapterRepository()
        self._bible = MockBibleRepository()
        self._branches = MockBranchRepository()
        
        self.outbox_service = MagicMock()
        self._chroma_additions = []
        self._chroma_deletions = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Simulate commit/rollback
        if exc_type is None:
            # Commit logic here if needed
            pass
        return False

    @property
    def books(self):
        return self._books

    @property
    def plots(self):
        return self._plots

    @property
    def chapters(self):
        return self._chapters

    @property
    def bible(self):
        return self._bible

    @property
    def branches(self):
        return self._branches

    def stage_chroma_add(self, collection, doc_id, doc_content, embedding, metadata=None):
        self._chroma_additions.append({"collection": collection, "id": doc_id})

    def stage_chroma_delete(self, collection, ids):
        self._chroma_deletions.append({"collection": collection, "ids": ids})

class BackendTestHarness:
    """
    A harness to coordinate LLM and DB mocks for backend verification.
    """
    def __init__(self):
        self.llm = MockGeminiApiClient()
        self.uow = MockUnitOfWork()
        
    async def setup_scenario(self, book_id: int, plot_data: List[Dict] = None, chapter_data: List[Dict] = None):
        """Pre-populate the mock database with a specific scenario."""
        import os
        os.environ['AUTH_DISABLED'] = 'false'
        os.environ['ALLOWED_API_KEYS'] = 'valid_key'

        # Create book
        await self.uow.books.create_book("Test Title", "Fantasy", 10)
        
        if plot_data:
            for p in plot_data:
                await self.uow.plots.save_plot(book_id, p)
        
        if chapter_data:
            for c in chapter_data:
                await self.uow.chapters.save_chapter(book_id, c)

    def mock_llm_response(self, prompt_keyword: str, response: Any, is_json: bool = False):
        if is_json:
            self.llm.add_json_response(prompt_keyword, response)
        else:
            self.llm.add_text_response(prompt_keyword, response)
