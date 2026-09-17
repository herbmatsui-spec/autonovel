import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.uow import UnitOfWork
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


def test_uow_all_repositories_instantiate_without_name_error():
    """UnitOfWorkの全18リポジトリプロパティがNameErrorなく正常に初期化・キャッシュされることを検証"""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value = mock_session

    uow = UnitOfWork(mock_db)
    uow.session = mock_session

    assert isinstance(uow.bible, BibleRepository)
    assert isinstance(uow.books, BookRepository)
    assert isinstance(uow.branches, BranchRepository)
    assert isinstance(uow.chapters, ChapterRepository)
    assert isinstance(uow.characters, CharacterRepository)
    assert isinstance(uow.misc, MiscRepository)
    assert isinstance(uow.plots, PlotRepository)
    assert isinstance(uow.rules, RulesRepository)
    assert isinstance(uow.audit, AuditRepository)
    assert isinstance(uow.book_scores, BookScoreRepository)
    assert isinstance(uow.prompt_versions, PromptVersionRepository)
    assert isinstance(uow.prompt_metrics, PromptMetricsRepository)
    assert isinstance(uow.pdca_history, PDCAHistoryRepository)
    assert isinstance(uow.illustrations, IllustrationRepository)
    assert isinstance(uow.collab, CollabRepository)
    assert isinstance(uow.cost, CostRepository)
    assert isinstance(uow.narrative_metrics, NarrativeMetricRepository)
    assert isinstance(uow.trace, TraceRepository)

    # キャッシュされていることを検証（同一インスタンスを返す）
    assert uow.pdca_history is uow.pdca_history
    assert uow.trace is uow.trace
    assert len(uow._repo_cache) == 18


@pytest.mark.asyncio
async def test_uow_cleanup_clears_repo_cache():
    """__aexit__ 完了後に _repo_cache が完全にクリアされることを検証"""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_db.get_session.return_value = mock_session

    uow = UnitOfWork(mock_db)
    uow.session = mock_session

    # アクセスしてキャッシュを生成
    _ = uow.pdca_history
    _ = uow.trace
    assert len(uow._repo_cache) == 2

    await uow.__aexit__(ValueError("test error"), None, None)
    assert len(uow._repo_cache) == 0
    assert uow.session is None
