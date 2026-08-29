import pytest

from src.engine_service import EngineService


def test_engine_service_initialization():
    """EngineServiceが正しく初期化できるかテスト"""
    service = EngineService(api_key="test-key")
    assert service is not None
    assert service.engine is not None


def test_engine_service_create_book():
    """EngineServiceで書籍作成ができるかテスト"""
    service = EngineService(api_key="test-key")
    book = service.create_book(title="Test Novel", genre="fantasy", target_eps=10)
    assert book["title"] == "Test Novel"
    assert book["genre"] == "fantasy"
    assert book["target_eps"] == 10
    assert book["id"] == 1


def test_engine_service_get_all_books():
    """EngineServiceで全書籍取得ができるかテスト"""
    service = EngineService(api_key="test-key")
    books = service.get_all_books()
    assert isinstance(books, list)
    assert len(books) == 0
