"""EditorialAssistantService の単体テスト."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.models.editor import (
    AskBibleRequest,
    ConsistencyAuditRequest,
)
from src.services.editorial_assistant_service import EditorialAssistantService


@pytest.fixture
def mock_deps():
    mock_rag = MagicMock()
    mock_rag.search_similar_chunks.return_value = ["アルトは古代魔導剣の継承者である。"]
    mock_rag.get_graph_context.return_value = [
        {"target_name": "王都ルミナス", "relation": "LOCATED_IN", "properties": {"status": "peace"}}
    ]
    mock_rag.rerank_graph_neighbors.return_value = [
        {"target_name": "王都ルミナス", "relation": "LOCATED_IN", "properties": {"status": "peace"}}
    ]

    mock_llm = MagicMock()
    mock_llm.generate_text = AsyncMock()

    mock_session = MagicMock()

    return mock_rag, mock_llm, mock_session


@pytest.mark.asyncio
async def test_ask_bible(mock_deps):
    """Ask Bible の Q&A テスト"""
    mock_rag, mock_llm, mock_session = mock_deps
    mock_result = MagicMock()
    mock_result.story_content = "アルトは第1章で王都ルミナスの地下遺跡を発見しました。"
    mock_llm.generate_text.return_value = mock_result

    service = EditorialAssistantService(rag_service=mock_rag, llm_gateway=mock_llm)
    req = AskBibleRequest(book_id=1, query="アルトが地下遺跡を見つけたのはどこ？")

    res = await service.ask_bible(mock_session, req)

    assert "アルトは第1章で" in res.answer
    assert len(res.evidence_nodes) >= 1
    assert "アルト" in res.related_characters


@pytest.mark.asyncio
async def test_audit_consistency_detected(mock_deps):
    """矛盾検出ありのテスト"""
    mock_rag, mock_llm, mock_session = mock_deps
    mock_result = MagicMock()
    mock_result.story_content = """
    ```json
    {
      "has_issues": true,
      "confidence_score": 0.9,
      "issues": [
        {
          "issue_type": "attribute",
          "severity": "error",
          "description": "アリスの目の色が青から赤に変わっています",
          "conflicting_text": "アリスの紅い瞳が輝いた",
          "suggested_fix": "碧い瞳に修正してください"
        }
      ]
    }
    ```
    """
    mock_llm.generate_text.return_value = mock_result

    service = EditorialAssistantService(rag_service=mock_rag, llm_gateway=mock_llm)
    req = ConsistencyAuditRequest(book_id=1, content="アリスの紅い瞳が輝いた")

    res = await service.audit_consistency(mock_session, req)

    assert res.has_issues is True
    assert len(res.issues) == 1
    assert res.issues[0].severity == "error"
    assert "アリスの目の色" in res.issues[0].description


@pytest.mark.asyncio
async def test_audit_consistency_clean(mock_deps):
    """矛盾なしのテスト"""
    mock_rag, mock_llm, mock_session = mock_deps
    mock_result = MagicMock()
    mock_result.story_content = '{"has_issues": false, "issues": [], "confidence_score": 1.0}'
    mock_llm.generate_text.return_value = mock_result

    service = EditorialAssistantService(rag_service=mock_rag, llm_gateway=mock_llm)
    req = ConsistencyAuditRequest(book_id=1, content="アルトは静かに歩き出した。")

    res = await service.audit_consistency(mock_session, req)

    assert res.has_issues is False
    assert len(res.issues) == 0
