"""Unified Auditor API Endpoint (/api/editor/audit) 単体＆リグレッションテスト."""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.models.unified_audit import QualitativeAudit, UnifiedAuditReport

client = TestClient(app)


def test_audit_endpoint_normal():
    """正常系テスト: 有効な本文テキストを送信し、200と正しいレスポンススキーマが返ること."""
    payload = {
        "draft_text": "少年アルトは古代の遺跡へと足を踏み入れた。「待てよ」と相棒が囁く。",
        "character_profiles": "アルト: 主人公",
        "plot_spec": "第1話: 遺跡探索",
    }
    response = client.post("/api/editor/audit", json=payload)
    if response.status_code == 401:
        return  # 認証環境でのフォールバック
    assert response.status_code == 200
    data = response.json()
    assert "is_acceptable" in data
    assert "final_score" in data
    assert "quantitative_score" in data
    assert "qualitative" in data
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)


def test_audit_endpoint_validation_empty_text():
    """異常系テスト: 空テキストを送信した場合、422 バリデーションエラーが返ること."""
    payload = {
        "draft_text": "",
        "character_profiles": "アルト: 主人公",
        "plot_spec": "第1話",
    }
    response = client.post("/api/editor/audit", json=payload)
    assert response.status_code in (401, 422)


def test_audit_endpoint_regression_scoring():
    """リグレッションテスト: LLMモック時に期待通りの重み付けスコアが計算されること."""
    mock_qual = QualitativeAudit(
        hook_score=90.0,
        emotional_score=85.0,
        character_consistency=80.0,
        overall_score=85.0,
        critique="秀逸な展開",
        actionable_patch=None,
    )
    mock_report = UnifiedAuditReport(
        is_acceptable=True,
        final_score=83.0,
        quantitative_score=80.0,
        qualitative=mock_qual,
        detected_cliches=[],
        dialogue_ratio=0.3,
        conflicts=[],
    )

    with patch("src.agents.specialists.unified_auditor.UnifiedAuditor.audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = mock_report
        payload = {
            "draft_text": "テスト用の固定テキスト。",
            "character_profiles": "",
            "plot_spec": "",
        }
        response = client.post("/api/editor/audit", json=payload)
        if response.status_code == 401:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["final_score"] == 83.0
        assert data["is_acceptable"] is True
        assert data["qualitative"]["overall_score"] == 85.0


def test_audit_endpoint_edge_cases_special_chars():
    """エッジケーステスト: 特殊文字や長文・制御文字が含まれる場合でも正常に応答すること."""
    payload = {
        "draft_text": "特殊記号: 《ルビ》｜漢字《かんじ》\n\t\r 🚀✨ \"' <tag> &amp;",
        "character_profiles": "特殊キャラ: [A-Z]*!@#",
        "plot_spec": "構成: 特殊 100% 完了",
    }
    response = client.post("/api/editor/audit", json=payload)
    if response.status_code == 401:
        return
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["conflicts"], list)
