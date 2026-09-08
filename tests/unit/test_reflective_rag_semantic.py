"""Unit tests for semantic reflective RAG, World Bible fit check, and prompt formatting (Part 3 / Steps 31-36)."""

import pytest
from unittest.mock import MagicMock

from src.services.reflective_rag import (
    ReflectiveRAGService,
    ReflectiveRetrievalResult,
    ReflectiveDoc,
    ContextFitResult,
)
from src.services.rag_service import SearchResult


def test_context_fit_check_world_bible_statuses():
    """Test World Bible consistency checks against retired/dead/sealed entities (Step 31)."""
    mock_rag = MagicMock()
    mock_rag.age_client = None
    service = ReflectiveRAGService(rag_service=mock_rag)
    mock_session = MagicMock()

    # Active normal entity
    doc_active = SearchResult(
        id="1", content="大賢者は王都の塔に滞在している。",
        metadata={"name": "大賢者", "status": "active"},
        source="world", score=0.9,
    )
    res_active = service._context_fit_check(mock_session, doc_active)
    assert res_active.score == 1.0
    assert res_active.is_retired is False

    # Dead / destroyed entity
    doc_dead = SearchResult(
        id="2", content="かつて存在した先代勇者の活躍。",
        metadata={"name": "先代勇者", "status": "dead"},
        source="world", score=0.9,
    )
    res_dead = service._context_fit_check(mock_session, doc_dead)
    assert res_dead.score == 0.0
    assert res_dead.is_retired is True
    assert "state_inactive" in res_dead.conflict_types

    # Forbidden / banned entity
    doc_forbidden = SearchResult(
        id="3", content="禁忌とされた暗黒魔法の書。",
        metadata={"name": "暗黒魔法", "status": "forbidden"},
        source="world", score=0.9,
    )
    res_forbidden = service._context_fit_check(mock_session, doc_forbidden)
    assert res_forbidden.score == 0.0
    assert res_forbidden.is_forbidden is True


@pytest.mark.asyncio
async def test_retrieve_reflective_async_api():
    """Test asynchronous reflective retrieval API entry point (Step 34)."""
    mock_rag = MagicMock()
    mock_rag.search_similar_chunks.return_value = [
        SearchResult(id="10", content="精霊の森の守護者に関する伝承", metadata={"title": "精霊伝承"}, source="world", score=0.8),
    ]

    service = ReflectiveRAGService(rag_service=mock_rag, max_iter=1)
    mock_session = MagicMock()

    result = await service.retrieve_reflective_async(
        session=mock_session,
        query="精霊の森の守護者",
        scene_intent="森への進入シーン",
    )

    assert isinstance(result, ReflectiveRetrievalResult)
    assert len(result.documents) == 1
    assert result.documents[0].search_result.id == "10"


def test_format_for_prompt():
    """Test formatting reflective retrieval results for prompt injection (Step 35)."""
    mock_rag = MagicMock()
    service = ReflectiveRAGService(rag_service=mock_rag)

    doc1 = SearchResult(
        id="1",
        content="古代都市ネオアトランティスは海深く沈んだ。",
        metadata={"title": "失われた古代都市"},
        source="lore",
        score=0.95,
    )
    r_doc1 = ReflectiveDoc(
        search_result=doc1,
        iteration_found=1,
        cosine_score=0.95,
        context_fit_score=1.0,
        context_fit_details=ContextFitResult(score=1.0),
        combined_score=0.95,
    )

    result = ReflectiveRetrievalResult(
        documents=[r_doc1],
        iterations=1,
        converged=True,
        original_query="古代都市",
    )

    formatted = service.format_for_prompt(result, max_chars=1000)
    assert "【参照世界観設定（反射的整合性検証済）】:" in formatted
    assert "失われた古代都市" in formatted
    assert "適合度: 0.95" in formatted
    assert "古代都市ネオアトランティスは海深く沈んだ。" in formatted

    # Empty result test
    empty_result = ReflectiveRetrievalResult(
        documents=[],
        iterations=1,
        converged=False,
        original_query="存在しない項目",
    )
    empty_formatted = service.format_for_prompt(empty_result)
    assert "該当する設定記述はありませんでした" in empty_formatted
