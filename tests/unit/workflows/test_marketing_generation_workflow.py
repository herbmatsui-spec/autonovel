"""MarketingGenerationWorkflow の契約テスト。

回帰防止: リポジトリの取得は facade 直下の get_book() でなければ AttributeError になる。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.workflows.marketing_generation_workflow import MarketingGenerationWorkflow


def _make_workflow(book):
    repo = MagicMock()
    # facade と同じ「メソッド直下」API のみ用意する。repo.books 等のネストは存在させない。
    repo.get_book = AsyncMock(return_value=book)
    repo.db = MagicMock()
    marketing = MagicMock()
    marketing.generate_pack = AsyncMock(return_value={"catchcopy": "テスト"})
    return MarketingGenerationWorkflow(repo=repo, marketing=marketing), marketing


@pytest.mark.asyncio
async def test_gets_book_via_facade_flat_call():
    book = MagicMock()
    book.title = "タイトル"
    book.synopsis = "あらすじ"
    wf, marketing = _make_workflow(book)
    result = await wf.execute(book_id=1, latest_ep=3)
    assert result == {"catchcopy": "テスト"}
    marketing.generate_pack.assert_awaited_once()


@pytest.mark.asyncio
async def test_raises_value_error_when_book_missing():
    wf, _ = _make_workflow(None)
    with pytest.raises(ValueError):
        await wf.execute(book_id=999, latest_ep=1)


@pytest.mark.asyncio
async def test_uses_repo_get_book_not_nested_attr():
    """`repo.books.get_by_id` のようなネスト参照を再度使わないことを固定する。"""
    book = MagicMock()
    book.title = "T"
    book.synopsis = "S"
    wf, _ = _make_workflow(book)
    await wf.execute(book_id=1, latest_ep=1)
    wf.repo.get_book.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_reporter_receives_progress():
    book = MagicMock()
    book.title = "T"
    book.synopsis = "S"
    wf, _ = _make_workflow(book)
    reporter = MagicMock()
    reporter.set_message = MagicMock()
    reporter.add_log = MagicMock()
    await wf.execute(book_id=1, latest_ep=1, reporter=reporter)
    reporter.set_message.assert_called()
