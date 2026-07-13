"""
tests/test_deai_auditor_edges.py
src/agents/audit.py の DeAIAuditor の尖り保全チェックテスト。
"""
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.audit import DeAIAuditor
from src.models.sharp_edge import SharpEdgeSpec


class TestDeAIAuditorEdges:
    def setup_method(self):
        self.auditor = DeAIAuditor(llm=MagicMock(), prompt_manager=None)

    def test_no_edges_returns_ok(self):
        import asyncio
        result = asyncio.run(self.auditor.audit("コンテンツ", edges=None))
        assert result == (True, "OK")

    def test_edges_preserved_returns_ok(self):
        edges = [SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")]
        import asyncio
        result = asyncio.run(self.auditor.audit("これはbefore after 余韻のある終わり方 です", before_content="before", edges=edges))
        assert result[0] is True

    def test_edges_removed_returns_false_with_message(self):
        edges = [SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")]
        import asyncio
        result = asyncio.run(self.auditor.audit("これは after で 余韻がない です", before_content="before", edges=edges))
        assert result[0] is False
        assert "ending_pullback" in result[1]
        assert "削られました" in result[1]

    def test_multiple_edges_one_removed(self):
        edges = [
            SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方"),
            SharpEdgeSpec(edge_type="protagonist_flaw", description="優柔不断な点"),
        ]
        after = "これは after で 優柔不断な点 だけ残った"
        import asyncio
        result = asyncio.run(self.auditor.audit(after, before_content="before", edges=edges))
        assert result[0] is False
        assert "ending_pullback" in result[1]
        assert "protagonist_flaw" not in result[1]
