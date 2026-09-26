"""執筆SSE（GET /api/stream/writing/{book_id}/{ep_num}）の契約テスト。

方針: DB・LLM に一切依存せず、外部接触3点（所有者検証 / 章リポジトリ / EpisodeWriter）を
テスト内で差し替える。開発機の autonovel.db が何であっても結果は同じ。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.auth import get_current_user
from src.backend.routers import stream_writing
from src.backend.server import app


class _FakeChapters:
    """uow.chapters の最小スタブ。"""

    def __init__(self) -> None:
        self.created: list[dict] = []

    async def get_chapter(self, branch_id: int, ep_num: int):
        return None  # 章未作成 → プレースホルダ経路を通す

    async def create_chapter(self, **kwargs):
        self.created.append(kwargs)
        return kwargs


class _FakeUow:
    """UnitOfWork の最小スタブ（async context manager として使う）。"""

    def __init__(self, session=None) -> None:
        self.session = session
        self.chapters = _FakeChapters()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEpisodeWriter:
    """LLM を呼ばずに執筆結果を返すスタブ。"""

    def __init__(self) -> None:
        pass

    async def write(self, **kwargs):
        return {"text": "テスト本文", "summary": "要約", "killer_phrase": "決め台詞"}


@pytest.fixture
def sse_env(monkeypatch):
    """SSE が外部接触しないよう差し替える。"""
    fake_uow = _FakeUow()
    monkeypatch.setattr(stream_writing, "UnitOfWork", lambda db=None: fake_uow)
    monkeypatch.setattr(
        stream_writing,
        "verify_book_ownership",
        AsyncMock(return_value=SimpleNamespace(id=1, user_id=1, genre="fantasy")),
    )
    monkeypatch.setattr(stream_writing, "EpisodeWriter", _FakeEpisodeWriter)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="user")
    yield fake_uow
    app.dependency_overrides.pop(get_current_user, None)


async def _get_sse(book_id: int = 1, ep_num: int = 1) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/stream/writing/{book_id}/{ep_num}?branch_id=1")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    return resp.text


@pytest.mark.asyncio
async def test_stream_writing_endpoint(sse_env):
    body = await _get_sse()
    assert '"phase": "Error"' not in body
    assert "ContextBuilding" in body
    assert "Complete" in body


@pytest.mark.asyncio
async def test_stream_writing_persists_chapter(sse_env):
    await _get_sse()
    assert len(sse_env.chapters.created) == 1
    assert sse_env.chapters.created[0]["content"] == "テスト本文"
