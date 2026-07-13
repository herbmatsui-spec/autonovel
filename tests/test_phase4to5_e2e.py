"""
tests/test_phase4to5_e2e.py
Phase 4-5 (改善案B: 尖り保全システム) の統合E2Eテスト。

尖り3件提案 -> 品質監査で角削除 -> rejected_edge_loss -> 再生成要求フロー
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.engine_critique import CritiqueAgent
from src.backend.engine_plot import resolve_sharp_edges
from src.backend.sharp_edge_preserver import check_edges_preserved
from src.models.db import PlotDbModel
from src.models.sharp_edge import SharpEdgeSpec
from src.agents.audit import DeAIAuditor


class TestPhase4To5Integration:
    def test_sharp_edges_roundtrip(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
            SharpEdgeSpec(edge_type="protagonist_flaw", description="優柔不断な点"),
            SharpEdgeSpec(edge_type="abnormal_dialogue", description="『退屈だね』という異常なセリフ"),
        ]
        plot = PlotDbModel(book_id=1, ep_num=1)
        plot.sharp_edges = edges
        plot.sharp_edges_json = json.dumps([e.model_dump() for e in edges])
        loaded = resolve_sharp_edges(plot)
        assert len(loaded) == 3
        assert loaded[0].edge_type == "ending_pullback"

    def test_edge_loss_detection(self):
        before = "余韻のある終わり方 優柔不断な点 異常なセリフ"
        after = "優柔不断な点 異常なセリフ"
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
        ]
        lost = check_edges_preserved(before, after, edges)
        assert len(lost) == 1
        assert lost[0].edge_type == "ending_pullback"

    def test_deai_auditor_rejects_edge_loss(self):
        import asyncio
        auditor = DeAIAuditor(llm=MagicMock(), prompt_manager=None)
        edges = [SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")]
        result = asyncio.run(auditor.audit("after without edge", before_content="before", edges=edges))
        assert result[0] is False
        assert "ending_pullback" in result[1]

    def test_deai_auditor_preserves_hook(self):
        import asyncio
        from src.models.emotional_hook import EmotionalHookSpec
        auditor = DeAIAuditor(llm=MagicMock(), prompt_manager=None)
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="長い苦悩の末に訪れる解放",
        )
        result = asyncio.run(auditor.audit(
            "after 長い苦悩の末に訪れる解放 です",
            before_content="before",
            emotional_hook=hook,
        ))
        assert result[0] is True
