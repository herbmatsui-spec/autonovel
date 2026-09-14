import pytest
from unittest.mock import MagicMock
from src.backend.database.uow import UnitOfWork

def test_uow_repository_properties():
    mock_db = MagicMock()
    uow = UnitOfWork(db=mock_db)
    uow.session = MagicMock()
    
    assert uow.books is not None
    assert uow.plots is not None
    assert uow.bible is not None
    assert uow.characters is not None
    assert uow.chapters is not None
    
    # 2回目のアクセスでキャッシュされた同一インスタンスが返ること
    first_books = uow.books
    assert uow.books is first_books