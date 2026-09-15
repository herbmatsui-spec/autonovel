import pytest
from unittest.mock import MagicMock
from src.backend.database.uow import UnitOfWork

def test_uow_repository_properties():
    mock_db = MagicMock()
    uow = UnitOfWork(db=mock_db)
    uow.session = MagicMock()
    
    # Check all repository properties
    assert uow.bible is not None
    assert uow.books is not None
    assert uow.branches is not None
    assert uow.chapters is not None
    assert uow.characters is not None
    assert uow.collab is not None
    assert uow.cost is not None
    assert uow.illustrations is not None
    assert uow.misc is not None
    assert uow.narrative_metrics is not None
    assert uow.pdca_history is not None
    assert uow.plots is not None
    assert uow.prompt_metrics is not None
    assert uow.prompt_versions is not None
    assert uow.rules is not None
    assert uow.trace is not None
    assert uow.book_scores is not None
    assert uow.audit is not None
    
    # 2回目のアクセスでキャッシュされた同一インスタンスが返ること
    first_books = uow.books
    assert uow.books is first_books