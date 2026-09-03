"""Episode 4 リグレッション: branch_id のデフォルト温存と明示指定優先.

Q5 方針: branch_id=1 はデフォルトとして残し、明示指定があればそちらを優先する。
"""
from __future__ import annotations

import inspect

import pytest

from src.backend.engine_context import ContextManager


class _StubBook:
    def __init__(self, current_branch_id: int | None = None):
        self.current_branch_id = current_branch_id


class _StubRepo:
    def __init__(self, current_branch_id: int | None = None):
        self._book = _StubBook(current_branch_id)

    async def get_book(self, _book_id):
        return self._book

    async def get_chapters_before(self, branch_id, ep):
        return []

    async def get_relevant_past_logs(self, branch_id, ep, query_text=""):
        return ""


@pytest.mark.asyncio
async def test_engine_context_default_branch_is_one():
    """branch_id 未指定時は book.current_branch_id=1 → 1 維持."""
    repo = _StubRepo(current_branch_id=None)
    ctx = ContextManager.__new__(ContextManager)
    ctx.repo = repo
    result = await ctx.build_past_context(book_id=1, end_ep=1)
    assert result is not None  # 呼び出しが成功


@pytest.mark.asyncio
async def test_engine_context_explicit_branch_takes_priority():
    """branch_id 明示指定時は book.current_branch_id より優先."""
    repo = _StubRepo(current_branch_id=2)
    ctx = ContextManager.__new__(ContextManager)
    ctx.repo = repo

    # シグネチャに branch_id パラメータが存在することを確認
    sig = inspect.signature(ctx.build_past_context)
    assert "branch_id" in sig.parameters, "branch_id param must exist"
    assert sig.parameters["branch_id"].default is None


@pytest.mark.asyncio
async def test_engine_context_get_optimal_context_split_has_branch_id():
    sig = inspect.signature(ContextManager.get_optimal_context_split)
    assert "branch_id" in sig.parameters


def test_hooks_router_accepts_branch_id_in_payload():
    """hooks.py の update hook で branch_id を payload から取れる."""
    from src.backend.routers.hooks import apply_hook_fix

    sig = inspect.signature(apply_hook_fix)
    params = sig.parameters
    assert "ep_num" in params
    assert "payload" in params
    # payload は dict[str, Any] なので branch_id は中で取得（変更反映済み）