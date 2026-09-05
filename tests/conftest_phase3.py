# tests/conftest_phase3.py
"""Phase 3 共通テストフィクスチャ・モック基盤"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.orchestrator import AgentContext
from src.utils.phase3_config import Phase3Config, load_phase3_config


@pytest.fixture(scope="session")
def phase3_config() -> Phase3Config:
    """Phase 3 テスト用設定"""
    # テスト用にオーバーライド可能な設定を返す
    return load_phase3_config()


@pytest.fixture
def mock_llm() -> MagicMock:
    """LLM クライアントのモック"""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value="Generated text response")
    mock.agenerate = AsyncMock(return_value="Generated text response")
    return mock


@pytest.fixture
def mock_graph_client() -> MagicMock:
    """GraphRAG クライアントのモック"""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=[])
    mock.query_single = AsyncMock(return_value=None)
    mock.add_node = AsyncMock()
    mock.add_edge = AsyncMock()
    mock.get_neighbors = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_redis() -> MagicMock:
    """Redis クライアントのモック"""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def sample_entities() -> list[dict[str, Any]]:
    """テスト用エンティティサンプル"""
    return [
        {"id": "e1", "name": "アレン", "type": "character", "aliases": ["主人公"]},
        {"id": "e2", "name": "エレナ", "type": "character", "aliases": ["魔法使い"]},
        {"id": "e3", "name": "魔王", "type": "character", "aliases": ["敵"]},
        {"id": "e4", "name": "剣", "type": "item", "aliases": []},
        {"id": "e5", "name": "王都", "type": "location", "aliases": ["首都"]},
    ]


@pytest.fixture
def sample_relations() -> list[dict[str, Any]]:
    """テスト用リレーションサンプル"""
    return [
        {"source": "e1", "target": "e2", "type": "同行", "weight": 1.0},
        {"source": "e1", "target": "e3", "type": "敵対", "weight": 1.0},
        {"source": "e1", "target": "e4", "type": "所持", "weight": 1.0},
        {"source": "e2", "target": "e5", "type": "所属", "weight": 0.8},
    ]


@pytest.fixture
def sample_context() -> dict[str, Any]:
    """テスト用コンテキストサンプル"""
    return {
        "book_id": 1,
        "branch_id": 1,
        "ep_num": 1,
        "artifacts": {
            "passion": 0.8,
            "target_word_count": 3000,
            "style_tag": "fantasy",
        },
    }


@pytest.fixture
def agent_context(sample_context: dict[str, Any]) -> AgentContext:
    """テスト用 AgentContext"""
    return AgentContext(
        book_id=sample_context["book_id"],
        branch_id=sample_context["branch_id"],
        ep_num=sample_context["ep_num"],
        artifacts=sample_context["artifacts"],
    )


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """イベントループ（セッションスコープ）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# 非同期フィクスチャのサンプル
@pytest.fixture
async def async_mock_llm() -> AsyncGenerator[MagicMock, None]:
    """非同期 LLM モック"""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value="Generated text")
    mock.agenerate = AsyncMock(return_value="Generated text")
    yield mock