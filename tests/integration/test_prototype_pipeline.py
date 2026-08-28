"""
tests/integration/test_prototype_pipeline.py - ステップ 16: Phase A 統合テスト
(1話 generate → score → foreshadow → polish → DB永続化)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from src.prototype.llm_adapter import GatewayLLMGenerator
from src.prototype.score_adapter import PrototypeScorer
from src.prototype.foreshadow_adapter import PersistentForeshadowManager
from src.prototype.polish_adapter import polish
from src.backend.workflows.narrative_state import NarrativeState


@pytest.fixture(autouse=True)
def override_settings():
    """Integration conftest の Docker/Testcontainers を回避"""
    yield


@pytest.mark.asyncio
async def test_prototype_pipeline_integration(tmp_path: Path):
    """Phase A 統合パイプラインの end-to-end 動作検証"""
    # 1. LLM Generator による生成
    mock_gw = MagicMock()
    mock_res = MagicMock()
    mock_res.story_content = "第1話：天空都市ルクスに光の石が燦然と輝いていた。"
    mock_gw.generate_text = AsyncMock(return_value=mock_res)

    generator = GatewayLLMGenerator(llm_gateway=mock_gw)
    gen_text = await generator.agenerate("プロット指示", target_chars=300, part_id=1, ep=1)
    assert "天空都市ルクス" in gen_text

    # 2. Score Reviewer による品質・商業スコアリング
    mock_quality = MagicMock()
    mock_q_rep = MagicMock()
    mock_q_rep.pacing_score = 0.88
    mock_q_rep.emotional_resonance = 0.85
    mock_q_rep.coherence_score = 0.90
    mock_q_rep.hook_retention = 0.80
    mock_quality.score_all = AsyncMock(return_value=mock_q_rep)

    mock_narrative = MagicMock()
    mock_narrative.score = AsyncMock(return_value={"overall_narrative_score": 85.0})

    scorer = PrototypeScorer(quality_scorer=mock_quality, narrative_scorer=mock_narrative)
    score_res = await scorer.score(1, gen_text)
    assert score_res.ep == 1
    assert score_res.total_score >= 0.80

    # 3. Foreshadow Manager による伏線管理と DB 永続化
    csv_file = tmp_path / "foreshadow.csv"
    cliffs_file = tmp_path / "cliffs.txt"
    fs_mgr = PersistentForeshadowManager(csv_path=csv_file, cliffs_path=cliffs_file)
    fs_mgr.foreshadows = [
        {"ep": 1, "type": "伏線", "text": "光脈の衰退の予兆", "status": "未回収"}
    ]

    mock_repo = MagicMock()
    db_store = {}

    async def fake_save(key, val):
        db_store[key] = val

    async def fake_get(key):
        return db_store.get(key)

    mock_repo.save_internal_state = AsyncMock(side_effect=fake_save)
    mock_repo.get_internal_state = AsyncMock(side_effect=fake_get)

    await fs_mgr.persist(book_id=10, branch_id=1, repo=mock_repo)
    assert "fs:10:1" in db_store

    loaded_fs = await fs_mgr.load_persistent(book_id=10, branch_id=1, repo=mock_repo)
    assert len(loaded_fs) == 1
    assert loaded_fs[0]["text"] == "光脈の衰退の予兆"

    # 4. Polish による最終校正と NarrativeState ハブの指摘反映
    hub = NarrativeState()
    hub.continuity_violations.append({"field": "symbol", "msg": "光の石の輝き設定に矛盾"})
    polished_text = polish(gen_text, scene={"erotic_intensity": 0}, hub=hub)

    assert "以下の矛盾を修正:" in polished_text
    assert "光の石の輝き設定に矛盾" in polished_text
    assert "天空都市ルクス" in polished_text
