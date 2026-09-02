"""Editor API Router の単体・統合テスト."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.backend.server import app

client = TestClient(app)


@pytest.fixture
def mock_assist_service():
    with patch("src.backend.routers.editor.assist_service") as mock:
        mock_res = MagicMock()
        mock_res.original_text = "男は扉を開けた。"
        mock_res.result_text = "重厚な鉄の扉が、軋んだ悲鳴を上げて開かれた。"
        mock_res.action = "describe"
        mock_res.diff_summary = "五感描写を拡張"
        mock.assist = AsyncMock(return_value=mock_res)
        yield mock


@pytest.fixture
def mock_editorial_service():
    with patch("src.backend.routers.editor.editorial_service") as mock:
        mock_ask_res = MagicMock()
        mock_ask_res.answer = "アルトは第1章で魔剣グラムを手に入れました。"
        mock_ask_res.evidence_nodes = [
            {"id": "魔剣グラム", "label": "Item", "properties": {}, "source_reference": "第1章"}
        ]
        mock_ask_res.related_characters = ["アルト"]
        mock.ask_bible = AsyncMock(return_value=mock_ask_res)

        mock_audit_res = MagicMock()
        mock_audit_res.has_issues = False
        mock_audit_res.issues = []
        mock_audit_res.confidence_score = 1.0
        mock.audit_consistency = AsyncMock(return_value=mock_audit_res)

        yield mock


@pytest.fixture
def mock_next_beats_service():
    with patch("src.backend.routers.editor.next_beats_service") as mock:
        mock_beats_res = MagicMock()
        mock_beats_res.beats = [
            {
                "card_id": "card_a",
                "branch_type": "royal",
                "title": "逆転の一撃",
                "summary": "アルトが反撃する",
                "content": "アルトの剣が閃いた。",
                "hook_text": "敵は倒れた。",
            }
        ]
        mock_beats_res.original_tail = "敵が迫る。"
        mock.generate_three_beats = AsyncMock(return_value=mock_beats_res)
        yield mock


def test_post_assist_endpoint(mock_assist_service):
    """POST /api/editor/assist 正常系テスト"""
    payload = {
        "text": "男は扉を開けた。",
        "action": "describe",
        "sensory_type": "auditory",
        "genre": "ハイファンタジー (R15)",
    }
    response = client.post("/api/editor/assist", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "describe"
    assert "軋んだ悲鳴" in data["result_text"]


def test_post_assist_validation_error():
    """POST /api/editor/assist バリデーションエラーテスト (空テキスト)"""
    payload = {
        "text": "",
        "action": "describe",
    }
    response = client.post("/api/editor/assist", json=payload)
    assert response.status_code == 422


def test_post_ask_bible_endpoint(mock_editorial_service):
    """POST /api/editor/ask-bible 正常系テスト"""
    payload = {
        "book_id": 1,
        "query": "アルトの魔剣について教えて",
    }
    response = client.post("/api/editor/ask-bible", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "魔剣グラム" in data["answer"]
    assert len(data["evidence_nodes"]) == 1


def test_post_audit_consistency_endpoint(mock_editorial_service):
    """POST /api/editor/audit-consistency 正常系テスト"""
    payload = {
        "book_id": 1,
        "content": "アルトは静かに剣を納めた。",
    }
    response = client.post("/api/editor/audit-consistency", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_issues"] is False


def test_post_next_beats_endpoint(mock_next_beats_service):
    """POST /api/editor/next-beats 正常系テスト"""
    payload = {
        "book_id": 1,
        "current_text": "敵の攻撃が激しさを増していく。",
        "genre": "ハイファンタジー (R15)",
    }
    response = client.post("/api/editor/next-beats", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["beats"]) == 1
    assert data["beats"][0]["title"] == "逆転の一撃"
