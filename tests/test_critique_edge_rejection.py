"""
tests/test_critique_edge_rejection.py
src/backend/engine_critique.py の尖り削除シナリオ統合テスト。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.engine_critique import CritiqueAgent
from src.models.sharp_edge import SharpEdgeSpec


class TestCritiqueEdgeRejection:
    @pytest.mark.asyncio
    async def test_edge_loss_rejected(self):
        repo = MagicMock()
        repo.get_book = AsyncMock(return_value=MagicMock(title="T", genre="test"))
        repo.get_all_non_anchor_chapters = AsyncMock(return_value=[
            MagicMock(ep_num=1, content="after content without edge")
        ])
        repo.get_all_plots = AsyncMock(return_value=[
            MagicMock(
                ep_num=1,
                detailed_blueprint="before blueprint",
                sharp_edges=[
                    SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")
                ]
            )
        ])
        repo.save_optimization_report = AsyncMock()
        repo.update_plot_quality_polish_status = AsyncMock()
        repo.save_pending_patch = AsyncMock(return_value=1)

        pm = MagicMock()
        pm.build_iterative_gap_analysis_prompt = AsyncMock(return_value="prompt")

        generate_json = AsyncMock(return_value=MagicMock(success=True, metadata={"prompt_patch": "patch"}))

        agent = CritiqueAgent(repo=repo, pm=pm, generate_json=generate_json)
        result = await agent.run_iterative_gap_analysis(book_id=1, max_iterations=10)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_edge_preserved_passes(self):
        repo = MagicMock()
        repo.get_book = AsyncMock(return_value=MagicMock(title="T", genre="test"))
        repo.get_all_non_anchor_chapters = AsyncMock(return_value=[
            MagicMock(ep_num=1, content="before after 余韻のある終わり方")
        ])
        repo.get_all_plots = AsyncMock(return_value=[
            MagicMock(
                ep_num=1,
                detailed_blueprint="before blueprint",
                sharp_edges=[
                    SharpEdgeSpec(edge_type="ending_pullback", description="余韻のある終わり方")
                ]
            )
        ])
        repo.save_optimization_report = AsyncMock()
        repo.save_pending_patch = AsyncMock(return_value=1)

        pm = MagicMock()
        pm.build_iterative_gap_analysis_prompt = AsyncMock(return_value="prompt")

        generate_json = AsyncMock(return_value=MagicMock(success=True, metadata={"prompt_patch": "patch"}))

        agent = CritiqueAgent(repo=repo, pm=pm, generate_json=generate_json)
        result = await agent.run_iterative_gap_analysis(book_id=1, max_iterations=10)
        assert result.success is True
