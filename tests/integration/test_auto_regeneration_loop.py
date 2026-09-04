# tests/integration/test_auto_regeneration_loop.py
"""自動再生成ループ E2E テスト"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.writing_service import WritingService
from src.agents.orchestrator import AgentContext
from src.services.book_score_service import BookScoreCalculator
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
from dataclasses import dataclass


@dataclass
class MockBookScore:
    """BookScoreCalculator.calculate の戻り値をモックするためのデータクラス"""
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float


class TestAutoRegenerationLoop:
    """自動再生成ループ E2E テスト"""
    
    @pytest.fixture
    def mock_writing_agent(self):
        agent = MagicMock()
        agent.execute = AsyncMock()
        return agent
    
    @pytest.fixture
    def mock_book_score_calculator(self):
        calc = MagicMock()
        calc.calculate = AsyncMock()
        return calc
    
    @pytest.fixture
    def mock_context_builder(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_illustration_agent(self):
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_auto_regeneration_success(
        self,
        mock_writing_agent,
        mock_book_score_calculator,
        mock_context_builder,
        mock_illustration_agent,
    ):
        """初回低スコア → 再生成 → 基準クリアの流れ"""
        from src.services.writing_service import WritingService
        
        # 初回: 低スコア、2回目: 基準クリア
        call_count = [0]
        
        async def mock_calculate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # 初回: 65点 (閾値70未満)
                return MockBookScore(
                    overall_score=65.0, structure_score=55.0, coherency_score=70.0,
                    factual_grounding_score=70.0, visual_textual_synergy_score=70.0,
                    reader_experience_score=65.0,
                )
            else:
                # 2回目: 75点 (基準クリア)
                return MockBookScore(
                    overall_score=75.0, structure_score=80.0, coherency_score=75.0,
                    factual_grounding_score=75.0, visual_textual_synergy_score=75.0,
                    reader_experience_score=75.0,
                )
        
        mock_book_score_calculator.calculate = mock_calculate
        
        # WritingAgent モック: 成功結果を返す
        from src.agents.orchestrator import AgentResult
        mock_writing_agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None,
            artifacts={"drafted_text": "生成された本文", "word_count": 3000},
        ))
        
        service = WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder,
            illustration_agent=mock_illustration_agent,
            max_retries=3,
            score_threshold=70.0,
        )
        
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        result = await service.generate_with_quality_assurance(ctx)
        
        # 検証
        assert call_count[0] == 2  # 初回 + 再生成後
        assert mock_writing_agent.execute.call_count == 2
        assert "regeneration_history" in ctx.artifacts
        assert len(ctx.artifacts["regeneration_history"]) == 1
        assert ctx.artifacts["regeneration_history"][0]["attempt"] == 1
        assert "structure" in ctx.artifacts["regeneration_history"][0]["low_dimensions"]
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(
        self,
        mock_writing_agent,
        mock_book_score_calculator,
        mock_context_builder,
        mock_illustration_agent,
    ):
        """最大リトライ超過で品質基準未達のまま返却"""
        from src.services.writing_service import WritingService
        
        # 常に低スコア
        async def mock_calculate(*args, **kwargs):
            return MockBookScore(
                overall_score=60.0, structure_score=50.0, coherency_score=60.0,
                factual_grounding_score=60.0, visual_textual_synergy_score=60.0,
                reader_experience_score=60.0,
            )
        
        mock_book_score_calculator.calculate = mock_calculate
        
        from src.agents.orchestrator import AgentResult
        mock_writing_agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None, artifacts={"drafted_text": "本文"},
        ))
        
        service = WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder,
            illustration_agent=mock_illustration_agent,
            max_retries=2,
            score_threshold=70.0,
        )
        
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        result = await service.generate_with_quality_assurance(ctx)
        
        # 3回実行 (初回 + 2回リトライ)
        assert mock_writing_agent.execute.call_count == 3
        assert "regeneration_history" in ctx.artifacts
        assert len(ctx.artifacts["regeneration_history"]) == 2  # max_retries=2 なので2回
    
    @pytest.mark.asyncio
    async def test_first_attempt_passes(
        self,
        mock_writing_agent,
        mock_book_score_calculator,
        mock_context_builder,
        mock_illustration_agent,
    ):
        """初回で基準クリア（再生成なし）"""
        from src.services.writing_service import WritingService
        
        # 初回で高スコア
        async def mock_calculate(*args, **kwargs):
            return MockBookScore(
                overall_score=85.0, structure_score=90.0, coherency_score=85.0,
                factual_grounding_score=85.0, visual_textual_synergy_score=85.0,
                reader_experience_score=85.0,
            )
        
        mock_book_score_calculator.calculate = mock_calculate
        
        from src.agents.orchestrator import AgentResult
        mock_writing_agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None, artifacts={"drafted_text": "本文"},
        ))
        
        service = WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder,
            illustration_agent=mock_illustration_agent,
            max_retries=3,
            score_threshold=70.0,
        )
        
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        result = await service.generate_with_quality_assurance(ctx)
        
        # 1回だけ実行
        assert mock_writing_agent.execute.call_count == 1
        assert "regeneration_history" not in ctx.artifacts or len(ctx.artifacts.get("regeneration_history", [])) == 0
    
    @pytest.mark.asyncio
    async def test_regeneration_focus_passed_to_context(
        self,
        mock_writing_agent,
        mock_book_score_calculator,
        mock_context_builder,
        mock_illustration_agent,
    ):
        """再生成時に regeneration_focus が context に設定される"""
        from src.services.writing_service import WritingService
        
        call_count = [0]
        
        async def mock_calculate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockBookScore(
                    overall_score=60.0, structure_score=50.0, coherency_score=70.0,
                    factual_grounding_score=70.0, visual_textual_synergy_score=65.0,
                    reader_experience_score=60.0,
                )
            else:
                return MockBookScore(
                    overall_score=75.0, structure_score=80.0, coherency_score=75.0,
                    factual_grounding_score=75.0, visual_textual_synergy_score=75.0,
                    reader_experience_score=75.0,
                )
        
        mock_book_score_calculator.calculate = mock_calculate
        
        from src.agents.orchestrator import AgentResult
        mock_writing_agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None, artifacts={"drafted_text": "本文"},
        ))
        
        service = WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder,
            illustration_agent=mock_illustration_agent,
            max_retries=3,
            score_threshold=70.0,
        )
        
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        await service.generate_with_quality_assurance(ctx)
        
        # 再生成時に context に正しい focus が設定される
        assert "regeneration_focus" in ctx.artifacts
        assert "regeneration_action" in ctx.artifacts
        # structure と reader_experience が低いので、優先度高い structure が選ばれる
        assert "structure" in ctx.artifacts["regeneration_focus"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])