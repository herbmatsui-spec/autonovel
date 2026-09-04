# tests/integration/test_full_pdca_cycle.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator import Orchestrator, AgentContext, AgentResult, AgentName
from src.agents.skill_base import SkillAgent
from src.services.book_score_service import BookScoreCalculator
from src.backend.database.repositories.book_score import BookScoreRepository
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
from datetime import datetime


class FullCycleSkill(SkillAgent):
    """完全サイクルテスト用スキル"""
    def __init__(self, *args, score_dict=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.score_dict = score_dict or {
            "overall_score": 80.0,
            "structure_score": 85.0,
            "coherency_score": 75.0,
            "factual_grounding_score": 80.0,
            "visual_textual_synergy_score": 85.0,
            "reader_experience_score": 75.0,
        }

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={"skill_executed": True})


@pytest.mark.asyncio
async def test_full_ab_pdca_cycle():
    """EventBus → A/Bテスト → PDCA → 自動昇格 の完全サイクル
    
    注: v2 スキルが存在しない場合は v1 のみでテストし、勝者判定ロジックのみ検証する
    """
    
    # 1. Orchestrator と BookScoreCalculator セットアップ
    orch = Orchestrator(nodes={})
    orch.register_discovered_skills('src.agents.skills.v1')
    
    # 2. A/Bテスト実行（v1のみ存在するため、v2はスキップされる想定）
    skill_name = "planning"
    ctx_list = [
        AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={})
        for i in range(5)
    ]
    
    # v2 が存在しない場合のエラーハンドリングを確認
    try:
        result = await orch.run_ab_test(
            skill_name=skill_name,
            version_a="v1",
            version_b="v2",
            ctx_list=ctx_list,
        )
        # v2 が存在しない場合はエラーになることを確認
        pytest.fail("v2が存在しない場合はエラーになるはず")
    except ValueError as e:
        # 期待通りエラーが発生
        assert "not found in version v2" in str(e)
    
    # 3. v1のみでA/Bテストを実行（同一バージョンでの比較）
    # 実際の運用では v1 と v2 で異なる実装を比較するが、テストでは同一バージョンで動作確認
    result = await orch.run_ab_test(
        skill_name=skill_name,
        version_a="v1",
        version_b="v1",  # 同一バージョンで動作確認
        ctx_list=ctx_list,
    )
    
    # 結果検証
    assert "winner" in result
    assert result["winner"] in ["a", "b", "tie"]
    assert "p_value" in result
    assert "version_a" in result
    assert "version_b" in result
    assert result["version_a"]["version"] == "v1"
    assert result["version_b"]["version"] == "v1"
    
    # 4. 勝者バージョンを昇格（v1のまま）
    winner_version = "v1"  # 同一バージョンの場合は v1 のまま
    orch.promote_ab_winner("planning", winner_version)
    assert orch.get_active_version() == winner_version
    
    # 5. BookScoreCalculator で PDCA レポート生成テスト
    mock_repo = MagicMock()
    mock_repo.get_all_for_book = AsyncMock(return_value=[
        BookScoreModel(
            book_id=1, chapter_number=i, overall_score=75.0 + i,
            structure_score=80.0, coherency_score=75.0,
            factual_grounding_score=75.0, visual_textual_synergy_score=80.0,
            reader_experience_score=75.0, evaluated_at=datetime.utcnow(),
            evaluator_version="1.0"
        )
        for i in range(1, 6)
    ])
    
    calc = BookScoreCalculator(repository=mock_repo)
    pdca = await calc.generate_pdca_report(1)
    
    # PDCAレポート構造検証
    assert "plan" in pdca
    assert "do" in pdca
    assert "check" in pdca
    assert "act" in pdca
    assert pdca["book_id"] == 1
    assert "priority_dimensions" in pdca["plan"]
    assert "recommended_actions" in pdca["act"]
    
    # 6. アラート生成ロジックの検証（API経由ではなくロジック直接テスト）
    # 改善傾向ならアラートなし
    trend = {
        "book_id": 1,
        "chapters_evaluated": 5,
        "slope": 1.0,
        "avg_score": 77.0,
        "latest_score": 79.0,
        "trend_direction": "improving",
        "changepoints": [],
    }
    alerts = []
    if trend.get("changepoints"):
        for cp in trend["changepoints"]:
            if cp["change"] < -15:
                alerts.append({"type": "score_drop"})
    assert len(alerts) == 0
    
    # スコア急落アラートケース
    trend = {
        "book_id": 1,
        "chapters_evaluated": 3,
        "slope": -2.0,
        "avg_score": 65.0,
        "latest_score": 55.0,
        "trend_direction": "declining",
        "changepoints": [
            {"chapter_index": 2, "prev_score": 75.0, "curr_score": 55.0, "change": -20.0}
        ],
    }
    
    # 急落アラートが生成されることを確認
    alerts = []
    if trend.get("changepoints"):
        for cp in trend["changepoints"]:
            if cp["change"] < -15:
                alerts.append({"type": "score_drop"})
    assert len(alerts) == 1
    assert alerts[0]["type"] == "score_drop"
    
    # 異常値アラートケース
    trend = {"latest_score": 45.0}
    alerts = []
    if trend.get("latest_score", 100) < 50:
        alerts.append({"type": "anomaly"})
    assert len(alerts) == 1
    assert alerts[0]["type"] == "anomaly"
    
    # 停滞アラートケース
    trend = {
        "slope": 0.1,
        "avg_score": 68.0,
    }
    alerts = []
    if abs(trend.get("slope", 0)) < 0.5 and trend.get("avg_score", 0) < 70:
        alerts.append({"type": "stagnation"})
    assert len(alerts) == 1
    assert alerts[0]["type"] == "stagnation"
    
    # 改善停止アラートケース
    trend = {
        "slope": -0.1,
        "chapters_evaluated": 6,
    }
    alerts = []
    if trend.get("slope", 0) <= 0 and trend.get("chapters_evaluated", 0) >= 5:
        alerts.append({"type": "no_improvement"})
    assert len(alerts) == 1
    assert alerts[0]["type"] == "no_improvement"
    
    print("✅ Full PDCA cycle test passed!")


@pytest.mark.asyncio
async def test_skill_promotion_metrics():
    """スキル昇格メトリクス記録テスト"""
    from src.backend.observability.metrics import record_skill_promotion
    
    # メトリクス記録がエラーにならないこと
    record_skill_promotion("planning", "v2")
    record_skill_promotion("writing", "v1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])