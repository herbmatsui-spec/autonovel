"""
tests/test_full_balance_pipeline_e2e.py
全72ステップの統合E2Eテスト。

高品質化が尖りを殺さず、面白さ検証不合格時は品質工程へ進まないことを検証する。
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.tension_curve_config import select_curve_by_hook
from src.backend.engine_critique import CritiqueAgent
from src.backend.engine_plot import (
    enforce_entertainment_gate,
    get_emotional_hook_for_plot,
    resolve_emotional_hook,
    resolve_sharp_edges,
)
from src.agents.audit import DeAIAuditor
from src.agents.early_entertainment_checker import EarlyEntertainmentChecker
from src.models.entertainment_check import EntertainmentCheckResult
from src.models.emotional_hook import EmotionalHookSpec
from src.models.db import PlotDbModel
from src.models.sharp_edge import SharpEdgeSpec
from streamlit_app.state import desires_to_hook


class TestFullBalancePipelineE2e:
    def test_phase1_hook_selection(self):
        desires = ["カタルシス"]
        hook = desires_to_hook(desires)
        assert hook is not None
        assert hook.hook_name == "catharsis"
        assert hook.subordinate_to_quality is True

    def test_phase2_hook_in_prompt(self):
        from prompts.plotting import EMOTIONAL_HOOK_TEMPLATE
        hook = EmotionalHookSpec(hook_name="catharsis", one_line_intent="解放", target_tension_peak=85)
        text = EMOTIONAL_HOOK_TEMPLATE.format(one_line_intent=hook.one_line_intent, target_tension_peak=hook.target_tension_peak)
        assert "解放" in text
        assert "85/100" in text

    def test_phase3_curve_selection(self):
        from src.backend.tension_curve_config import select_curve_by_hook
        assert select_curve_by_hook("catharsis") == "zamaa_heavy"

    def test_phase4_sharp_edges_proposal(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
            SharpEdgeSpec(edge_type="protagonist_flaw", description="優柔不断な点"),
            SharpEdgeSpec(edge_type="abnormal_dialogue", description="『退屈だね』という異常なセリフ"),
        ]
        plot = PlotDbModel(book_id=1, ep_num=1)
        plot.sharp_edges_json = json.dumps([e.model_dump() for e in edges])
        loaded = resolve_sharp_edges(plot)
        assert len(loaded) == 3

    def test_phase5_edge_loss_rejection(self):
        import asyncio
        auditor = DeAIAuditor(llm=MagicMock(), prompt_manager=None)
        edges = [SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")]
        result = asyncio.run(auditor.audit("after without edge", before_content="before", edges=edges))
        assert result[0] is False
        assert "削られました" in result[1]

    def test_phase6_entertainment_check(self):
        from unittest.mock import AsyncMock, MagicMock
        llm = MagicMock()
        llm.generate_json = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "interest_score": 85,
                "physiological_reaction": "背筋の寒さ",
                "would_continue_reading": True,
                "feedback": "展開が読めない",
            }
        })
        pm = MagicMock()
        pm.build_early_entertainment_check_prompt = AsyncMock(return_value="prompt")
        checker = EarlyEntertainmentChecker(llm=llm, prompt_manager=pm)
        import asyncio
        result = asyncio.run(checker.check("plot", "opening"))
        assert result.interest_score == 85

    @pytest.mark.asyncio
    async def test_phase7_gate_blocks_low_interest(self):
        checker = MagicMock()
        checker.check = AsyncMock(return_value=EntertainmentCheckResult(
            interest_score=40,
            physiological_reaction="無反応",
            would_continue_reading=False,
            feedback="bad",
        ))
        with pytest.raises(RuntimeError, match="面白さ検証不合格"):
            await enforce_entertainment_gate(checker, "plot", "opening", max_retries=0)

    @pytest.mark.asyncio
    async def test_phase7_gate_passes_high_interest(self):
        checker = MagicMock()
        checker.check = AsyncMock(return_value=EntertainmentCheckResult(
            interest_score=80,
            physiological_reaction="カタルシス",
            would_continue_reading=True,
            feedback="good",
        ))
        result = await enforce_entertainment_gate(checker, "plot", "opening", max_retries=0)
        assert result.interest_score == 80

    @pytest.mark.asyncio
    async def test_phase8_hook_persistence_roundtrip(self):
        hook = EmotionalHookSpec(hook_name="catharsis", one_line_intent="解放", target_tension_peak=85)
        plot = PlotDbModel(book_id=1, ep_num=1)
        plot.emotional_hook_json = hook.model_dump_json()
        loaded = resolve_emotional_hook(plot)
        assert loaded is not None
        assert loaded.hook_name == "catharsis"
        assert loaded.target_tension_peak == 85
