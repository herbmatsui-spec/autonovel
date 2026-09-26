"""DataRepositoryFacade の契約（メソッド直下呼び出し専用）を固定する。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.backend.database.repository import DataRepositoryFacade
from src.backend.database.uow_context import current_uow


def test_getattr_returns_coroutine_function():
    facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
    attr = facade.anything
    assert callable(attr)
    assert attr.__name__ == "wrapper"


def test_nested_repository_access_is_not_supported():
    """`facade.books.get_book()` は動かない（attr は coroutine function）。"""
    facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
    assert not hasattr(facade.books, "get_book")
    assert not hasattr(facade.books, "get_by_id")


@pytest.mark.asyncio
async def test_unknown_attribute_raises_attribute_error():
    """未知のメソッドを呼び出すと AttributeError が発生すること。"""
    dummy_uow = SimpleNamespace(
        books=SimpleNamespace(),
        plots=SimpleNamespace(),
        chapters=SimpleNamespace(),
        characters=SimpleNamespace(),
        branches=SimpleNamespace(),
        bible=SimpleNamespace(),
        misc=SimpleNamespace(),
        rules=SimpleNamespace(),
        audit=SimpleNamespace(),
        prompt_versions=SimpleNamespace(),
        illustrations=SimpleNamespace(),
    )
    token = current_uow.set(dummy_uow)
    try:
        facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
        with pytest.raises(AttributeError, match="has no attribute 'totally_unknown'"):
            await facade.totally_unknown()
    finally:
        current_uow.reset(token)
