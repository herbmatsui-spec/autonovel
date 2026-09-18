"""二層ハイブリッド監査 (Two-Tier Hybrid Audit) E2E 結合テスト."""
import time
import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.agents.specialists.unified_auditor import UnifiedAuditor

client = TestClient(app)


@pytest.mark.asyncio
async def test_hybrid_auditor_direct_execution_e2e():
    """正常系E2E: UnifiedAuditor を直接実行し、二層（静的＋定性）の完全結果を取得."""
    text = (
        "「お前が勇者アルトか」黒衣の男は低く笑った。\n"
        "アルトは無言で聖剣の柄に手を掛けた。\n"
        "夜風が荒野の砂塵を巻き上げ、二人の間に緊張が走る。"
    )
    auditor = UnifiedAuditor(llm_gateway=None)
    start_time = time.perf_counter()
    report = await auditor.audit(
        text=text,
        character_profiles="アルト: 寡黙な若き勇者\n黒衣の男: 暗殺組織の執行人",
        plot_spec="第1話: 荒野での遭遇と一騎打ちの予兆",
    )
    duration = time.perf_counter() - start_time

    # パフォーマンス検証: LLM gateway=None 時は瞬時（0.5秒未満）に完了すること
    assert duration < 0.5

    # データ整合性検証
    assert 0.0 <= report.final_score <= 100.0
    assert 0.0 <= report.quantitative_score <= 100.0
    assert isinstance(report.is_acceptable, bool)
    assert isinstance(report.conflicts, list)
    assert report.qualitative is not None
    assert 0.0 <= report.qualitative.hook_score <= 100.0


def test_hybrid_audit_api_e2e():
    """API統合E2E: POST /api/editor/audit から二層監査を実行."""
    payload = {
        "draft_text": (
            "「待て！」背後から鋭い叫び声が響いた。"
            "振り返ると、銀髪の少女が息を切らして立っていた。"
            "その手には、失われたはずの古代魔法書が握られていた。"
        ),
        "character_profiles": "アルト: 主人公, ルナ: 魔法学院の特待生",
        "plot_spec": "第2話: 魔法書の奪還",
    }
    response = client.post("/api/editor/audit", json=payload)
    if response.status_code == 401:
        pytest.skip("認証が必要な環境")

    assert response.status_code == 200
    data = response.json()
    assert "final_score" in data
    assert "quantitative_score" in data
    assert "is_acceptable" in data
    assert "qualitative" in data
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)


def test_hybrid_audit_api_empty_text_error():
    """異常系E2E: 空文字テキスト送信時の422エラーハンドリング検証."""
    payload = {
        "draft_text": "",
        "character_profiles": "",
        "plot_spec": "",
    }
    response = client.post("/api/editor/audit", json=payload)
    assert response.status_code in (401, 422)
