"""Integration tests for ReflectiveRAGService and ContextBuilderAgent (Step 24)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.orchestrator import AgentContext
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import GraphRAGService, SearchResult


@pytest.fixture
def sample_candidates():
    return [
        SearchResult(
            id="doc-1",
            content="古代魔法アルカディアは王都で使われた。",
            metadata={"entity_name": "アルカディア", "is_forbidden": False},
            source="vector",
            score=0.95,
        ),
        SearchResult(
            id="doc-2",
            content="禁忌魔法カオス・ヴォイドは世界の理を乱す。",
            metadata={"entity_name": "カオス・ヴォイド", "is_forbidden": True},
            source="vector",
            score=0.92,
        ),
        SearchResult(
            id="doc-3",
            content="剣士レオンの旅立ちと誓い。",
            metadata={"entity_name": "レオン", "is_forbidden": False},
            source="vector",
            score=0.88,
        ),
    ]


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.session = MagicMock()
    
    plot_mock = MagicMock()
    plot_mock.summary = "王都での戦いと魔法の真実"
    plot_mock.title = "第1話：胎動"
    plot_mock.tension = 65
    plot_mock.detailed_blueprint = "詳細プロット概要"
    plot_mock.scenes = ["シーン1", "シーン2"]
    plot_mock.current_chain_phase = "Friction"
    plot_mock.is_catharsis = False
    plot_mock.model_dump.return_value = {
        "summary": "王都での戦いと魔法の真実",
        "title": "第1話：胎動",
        "tension": 65,
        "detailed_blueprint": "詳細プロット概要",
        "scenes": ["シーン1", "シーン2"],
        "current_chain_phase": "Friction",
    }
    repo.get_plot = AsyncMock(return_value=plot_mock)
    
    # Mock get_book, get_all_characters, get_prev_chapter
    repo.get_book = AsyncMock(return_value={"id": 1, "title": "テスト小説"})
    char_mock = MagicMock()
    char_mock.name = "レオン"
    repo.get_all_characters = AsyncMock(return_value=[char_mock])
    repo.get_prev_chapter = AsyncMock(return_value=None)
    return repo


@pytest.mark.asyncio
async def test_context_builder_with_reflective_rag_success(mock_repo, sample_candidates):
    """ReflectiveRAGServiceとContextBuilderAgentの統合テスト：正常系."""
    mock_rag = MagicMock(spec=GraphRAGService)
    mock_rag.search_similar_chunks.return_value = sample_candidates
    mock_rag.age_client = None

    reflective_rag = ReflectiveRAGService(
        rag_service=mock_rag,
        top_k=2,
        max_iter=2,
        relevance_threshold=0.5,
    )

    agent = ContextBuilderAgent(repo=mock_repo, reflective_rag=reflective_rag)

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"repo": mock_repo},
    )

    res = await agent.execute(ctx)

    assert res.error is None
    writing_ctx = res.artifacts.get("writing_context", {})
    assert "rag_context" in writing_ctx
    rag_docs = writing_ctx["rag_context"]

    # 禁忌魔法 (doc-2, is_forbidden=True) は _context_fit_check で 0.0 点となり
    # 0.6 * 0.92 + 0.4 * 0 = 0.552 だが、閾値0.6等で制御されるか正常ドキュメントが優先される
    assert len(rag_docs) > 0
    # doc-1 が含まれていること
    contents = [d["content"] for d in rag_docs]
    assert any("古代魔法アルカディア" in c for c in contents)


@pytest.mark.asyncio
async def test_context_builder_reflective_rag_forbidden_filtering(mock_repo, sample_candidates):
    """世界観整合性違反のドキュメントがペナルティ減点され除外されることの検証."""
    mock_rag = MagicMock(spec=GraphRAGService)
    # doc-2 のみ is_forbidden
    mock_rag.search_similar_chunks.return_value = sample_candidates
    mock_rag.age_client = None

    reflective_rag = ReflectiveRAGService(
        rag_service=mock_rag,
        top_k=2,
        max_iter=1,
        relevance_threshold=0.6,  # 0.6 * 0.92 + 0.4 * 0.0 = 0.552 < 0.6 なので除外される
    )

    agent = ContextBuilderAgent(repo=mock_repo, reflective_rag=reflective_rag)

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"repo": mock_repo},
    )

    res = await agent.execute(ctx)
    writing_ctx = res.artifacts["writing_context"]
    rag_docs = writing_ctx["rag_context"]

    # doc-2 が除外されていることを検証
    for doc in rag_docs:
        assert "禁忌魔法カオス・ヴォイド" not in doc["content"]


@pytest.mark.asyncio
async def test_context_builder_reflective_rag_timeout_fallback(mock_repo, sample_candidates):
    """検索タイムアウト発生時に安全にフォールバックすることの検証."""
    mock_rag = MagicMock(spec=GraphRAGService)
    mock_rag.search_similar_chunks.return_value = sample_candidates

    # timeout_seconds を 0.0001 (極小) に設定して意図的にタイムアウトを誘発
    reflective_rag = ReflectiveRAGService(
        rag_service=mock_rag,
        top_k=2,
        max_iter=3,
        timeout_seconds=0.000001,
    )

    agent = ContextBuilderAgent(repo=mock_repo, reflective_rag=reflective_rag)

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"repo": mock_repo},
    )

    res = await agent.execute(ctx)
    assert res.error is None
    writing_ctx = res.artifacts["writing_context"]
    assert "rag_context" in writing_ctx


@pytest.mark.asyncio
async def test_context_builder_without_reflective_rag(mock_repo):
    """reflective_rag未指定時の下位互換性テスト."""
    agent = ContextBuilderAgent(repo=mock_repo, reflective_rag=None)

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"repo": mock_repo},
    )

    res = await agent.execute(ctx)
    assert res.error is None
    writing_ctx = res.artifacts["writing_context"]
    assert writing_ctx["rag_context"] == []
