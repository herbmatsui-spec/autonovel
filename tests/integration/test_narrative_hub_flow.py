"""
tests/integration/test_narrative_hub_flow.py - Phase 3: MasterGraph と NarrativeState の統合テスト
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.backend.workflows.narrative_state import NarrativeState
from src.backend.workflows.graphs.master_graph import (
    SequentialMasterGraphFallback,
    should_revise_writing,
)
from src.backend.workflows.state import MasterGraphState


@pytest.fixture(autouse=True)
def override_settings():
    """Docker 不要でローカル実行するための fixture オーバーライド"""
    yield


def test_should_revise_writing_with_continuity_violation():
    """ステップ 18: 連続性違反による revise 判定"""
    hub = NarrativeState()
    hub.continuity_violations.append({"ep": 2, "field": "hp", "msg": "HP sudden jump"})

    state: MasterGraphState = {
        "revision_budget": 2,
        "narrative": hub,
        "review_results": {
            1: {"requires_revision": False},
            2: {"requires_revision": False},
        },
    }

    decision = should_revise_writing(state)
    assert decision == "revise_phase"
    assert 2 in state.get("needs_revision_eps", [])


def test_should_revise_writing_with_affinity_drop():
    """ステップ 18: 好感度低下による revise 判定"""
    hub = NarrativeState()
    hub.upsert_episode(1, affinity={"メインヒロイン": 80.0})
    hub.upsert_episode(2, affinity={"メインヒロイン": 50.0})

    state: MasterGraphState = {
        "revision_budget": 1,
        "narrative": hub,
        "review_results": {
            1: {"requires_revision": False},
            2: {"requires_revision": False},
        },
    }

    decision = should_revise_writing(state)
    assert decision == "revise_phase"
    assert 2 in state.get("needs_revision_eps", [])


@pytest.mark.asyncio
async def test_narrative_hub_full_master_flow():
    """ステップ 15, 16, 17, 19, 20: SequentialMasterGraphFallback を用いた NarrativeState 連動フロー"""
    hub = NarrativeState(book_id=101, branch_id=1)

    initial_state: MasterGraphState = {
        "task_id": "test_narrative_task",
        "mode": "full_pipeline",
        "book_id": 101,
        "branch_id": 1,
        "target_start_ep": 1,
        "target_end_ep": 2,
        "revision_budget": 1,
        "narrative": hub,
        "metadata": {"genre": "ファンタジー", "theme": "絆と成長"},
    }

    # 各サブグラフ実行をモックして高速かつ確実に検証
    mock_plot_result = {"is_approved": True, "raw_plot_draft": "勇者の旅立ち"}
    
    mock_draft_ep1 = "第1話の本文。勇者はメインヒロインに出会い、ありがとうと笑顔を交わす。"
    mock_draft_ep2 = "第2話の本文。冷たい風の中、二人は信じる心で手を取り合う。"

    async def fake_plot_ainvoke(inputs):
        return mock_plot_result

    async def fake_writing_ainvoke(inputs):
        ep = inputs["ep_num"]
        content = mock_draft_ep1 if ep == 1 else mock_draft_ep2
        return {
            "ep_num": ep,
            "draft_content": content,
            "status": "draft_generated",
            "quality_score": 88.0,
        }

    async def fake_review_ainvoke(inputs):
        ep = inputs["ep_num"]
        # ep 2 に要修正を設定して revise ループを発火
        req_rev = (ep == 2 and "前回の推敲指摘" not in inputs.get("source_content", ""))
        return {
            "ep_num": ep,
            "requires_revision": req_rev,
            "commercial_score": 85.0 if not req_rev else 65.0,
            "revision_instructions": ["テンションを高めてください。"] if req_rev else [],
        }

    with patch("src.backend.workflows.nodes.master_nodes.compile_plot_graph") as mock_comp_plot, \
         patch("src.backend.workflows.nodes.master_nodes.compile_writing_graph") as mock_comp_write, \
         patch("src.backend.workflows.nodes.master_nodes.compile_review_graph") as mock_comp_rev:

        mock_plot_app = MagicMock()
        mock_plot_app.ainvoke = AsyncMock(side_effect=fake_plot_ainvoke)
        mock_comp_plot.return_value = mock_plot_app

        mock_write_app = MagicMock()
        mock_write_app.ainvoke = AsyncMock(side_effect=fake_writing_ainvoke)
        mock_comp_write.return_value = mock_write_app

        mock_rev_app = MagicMock()
        mock_rev_app.ainvoke = AsyncMock(side_effect=fake_review_ainvoke)
        mock_comp_rev.return_value = mock_rev_app

        runner = SequentialMasterGraphFallback()
        final_state = await runner.ainvoke(initial_state)

    # ハブの検証
    res_hub = final_state.get("narrative")
    assert res_hub is not None
    assert isinstance(res_hub, NarrativeState)

    # 各話の品質スコア・好感度・官能メトリクスが埋まっていること
    assert 1 in res_hub.episodes
    assert 2 in res_hub.episodes
    assert 1 in res_hub.quality_scores
    assert 2 in res_hub.quality_scores
    assert 1 in res_hub.erotic_metrics
    assert 2 in res_hub.erotic_metrics
    assert len(res_hub.affinity_map) > 0

    # レポートが quality_metrics および narrative_report に反映されていること
    assert "narrative" in final_state.get("quality_metrics", {})
    assert final_state["narrative_report"]["book_id"] == 101
