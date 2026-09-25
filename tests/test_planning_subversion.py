# tests/test_planning_subversion.py
import pytest
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, '.')

from src.agents.planning import PlanningAgent
from src.models.plot import ArcList, ArcBlueprint


class TestPlanningSubversion:
    @pytest.fixture
    def agent(self):
        llm = MagicMock()
        llm.generate_json = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "arcs": [
                    {"arc_num": 1, "start_ep": 1, "end_ep": 10, "title": "序章", "summary": "test"}
                ]
            }
        })
        pm = MagicMock()
        pm.build_arc_generation_prompt.return_value = "prompt"
        # render_async for beat_sheet
        pm.render_async = AsyncMock(return_value="prompt")
        return PlanningAgent(llm=llm, prompt_manager=pm)

    @pytest.mark.asyncio
    async def test_generate_arcs_injects_subversion(self, agent):
        arcs = await agent.generate_arcs("Test", "Synopsis", 10, subversion_enabled=True)
        # アーク内の thematic_milestone に裏切り文言
        assert any("裏切り" in arc.thematic_milestone for arc in arcs.arcs)

    @pytest.mark.asyncio
    async def test_generate_arcs_no_subversion_when_disabled(self, agent):
        arcs = await agent.generate_arcs("Test", "Synopsis", 10, subversion_enabled=False)
        assert all("裏切り" not in arc.thematic_milestone for arc in arcs.arcs)

    @pytest.mark.asyncio
    async def test_generate_beat_sheet_injects_subversion(self, agent):
        # Mock the LLM to return CSV data for beat sheet (12 episodes to get 3,6,9)
        agent.llm.generate_json = AsyncMock(return_value={
            "success": True,
            "data": "話数,フェーズ,ミッション,テンション,ビジュアル\n1,導入,test,0.5,scene1\n2,展開,test,0.6,scene2\n3,結末,test,0.7,scene3\n4,導入,test,0.5,scene4\n5,展開,test,0.6,scene5\n6,結末,test,0.7,scene6\n7,導入,test,0.5,scene7\n8,展開,test,0.6,scene8\n9,結末,test,0.7,scene9\n10,導入,test,0.5,scene10\n11,展開,test,0.6,scene11\n12,結末,test,0.7,scene12"
        })
        beats = await agent.generate_commercial_beat_sheet("Test", "Synopsis", subversion_enabled=True)
        subversion_beats = [b for b in beats if "裏切り" in b.mission]
        # At least episodes 3, 6, 9 should have subversion
        assert len(subversion_beats) >= 3

    @pytest.mark.asyncio
    async def test_generate_beat_sheet_no_subversion_when_disabled(self, agent):
        agent.llm.generate_json = AsyncMock(return_value={
            "success": True,
            "data": "話数,フェーズ,ミッション,テンション,ビジュアル\n1,導入,test,0.5,scene1\n2,展開,test,0.6,scene2\n3,結末,test,0.7,scene3"
        })
        beats = await agent.generate_commercial_beat_sheet("Test", "Synopsis", subversion_enabled=False)
        subversion_beats = [b for b in beats if "裏切り" in b.mission]
        assert len(subversion_beats) == 0

    @pytest.mark.asyncio
    async def test_execute_exposes_subversion_engine(self, agent):
        # Mock ctx
        ctx = MagicMock()
        ctx.book_id = "test_book"
        ctx.artifacts = {
            "title": "Test Novel",
            "synopsis": "Test synopsis",
            "target_eps": 10,
            "start_ep": 1,
            "subversion_enabled": True,
        }
        
        result = await agent.execute(ctx)
        
        # Check that subversion_engine is in artifacts
        assert "subversion_engine" in result.artifacts
        engine_data = result.artifacts["subversion_engine"]
        assert "schedule" in engine_data
        assert len(engine_data["schedule"]) > 0
        # Check that schedule has correct structure
        for entry in engine_data["schedule"]:
            assert "trigger_ep" in entry
            assert "pattern_type" in entry

    @pytest.mark.asyncio
    async def test_proposal_gacha_passes_kwargs(self, agent):
        ctx = MagicMock()
        ctx.book_id = "test_book"
        ctx.artifacts = {
            "title": "Test Novel",
            "synopsis": "Test synopsis",
            "target_eps": 10,
            "start_ep": 1,
            "proposal_gacha": True,
            "subversion_seed": "test_seed",
        }
        
        # We need to mock generate_proposals_isolated to avoid complex sandbox setup
        with patch.object(agent, 'generate_proposals_isolated', new_callable=AsyncMock) as mock_proposals:
            mock_proposals.return_value = {
                "proposal_a": {"proposal_id": "proposal_a", "title": "Test (Variant A)", "arcs": {"arcs": []}},
                "proposal_b": {"proposal_id": "proposal_b", "title": "Test (Variant B)", "arcs": {"arcs": []}},
                "proposal_c": {"proposal_id": "proposal_c", "title": "Test (Variant C)", "arcs": {"arcs": []}},
            }
            result = await agent.execute(ctx)
            mock_proposals.assert_called_once()
            # Check that subversion_seed was passed
            call_kwargs = mock_proposals.call_args.kwargs
            assert "subversion_seed" in call_kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])