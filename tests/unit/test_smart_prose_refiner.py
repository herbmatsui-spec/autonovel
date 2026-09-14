"""
Unit tests for Smart Prose Refiner.
PLAN 14 - Step 12: スマート校正LLM＆商業ラノベFew-Shot動的注入 実装計画書
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
import pytest

from src.models.prose_refinement import ProseRefineResult
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm_service import LLMService
from src.agents.writing.prose_refiner_agent import ProseRefinerAgent


class MockLLMAdapterForProseRefinement(MockLLMAdapter):
    """モック LLM アダプタ - 文体推敲用特殊レスポンス"""
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        # 特定のプロンプトに対して特殊なレスポンスを返す
        if "言うまでもないが、彼は天才だった" in prompt:
            return "言うまでもなく、彼の才能は群を抜いていた。"
        elif "彼は剣を振り下ろした。敵は驚いていた。" in prompt:
            return "銀の剣が風を裂き、鋭い破風音を立てて叩き込まれた。相手の瞳に驚愕の色が走り、胸当てが激しく響いた。"
        else:
            # デフォルトは元のテキストを返す（変更なし）
            if "入力テキスト" in prompt:
                lines = prompt.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('#') and '入力テキスト' not in line:
                        return line.strip()
            return "元のテキストが返されました（モック）" 


@pytest.mark.asyncio
async def test_prose_refiner_grammatical_integrity():
    """文法崩壊（主語欠落等）が起きないことをテスト"""
    mock_adapter = MockLLMAdapterForProseRefinement()
    mock_llm_service = LLMService()
    mock_llm_service.adapter = mock_adapter
    
    agent = ProseRefinerAgent(llm_service=mock_llm_service)
    
    test_text1 = "言うまでもないが、彼は天才だった" 
    result1 = await agent.refine(test_text1, genre="fantasy_action")
    
    assert isinstance(result1, ProseRefineResult)
    assert result1.refined_text is not None
    assert len(result1.refined_text) > 0
    
    refined = result1.refined_text
    assert not refined.startswith("、彼"), f"主語欠落の可能性: {refined}"
    assert not refined.startswith("、"), f"不自然な開始: {refined}"
    assert "天才" in refined or "才能" in refined, f"重要な概念が失われている: {refined}"


@pytest.mark.asyncio
async def test_prose_refiner_specific_transformation():
    """特定の例文の変換をテスト"""
    mock_adapter = MockLLMAdapterForProseRefinement()
    mock_llm_service = LLMService()
    mock_llm_service.adapter = mock_adapter
    
    agent = ProseRefinerAgent(llm_service=mock_llm_service)
    
    test_text = "言うまでもないが、彼は天才だった" 
    expected_refined = "言うまでもなく、彼の才能は群を抜いていた。"
    
    result = await agent.refine(test_text, genre="fantasy_action")
    
    assert isinstance(result, ProseRefineResult)
    assert result.refined_text == expected_refined, f"期待: {expected_refined}, 実際: {result.refined_text}"
    assert result.total_fixes_count >= 0
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_prose_refiner_no_grammatical_errors_in_action_scene():
    """アクションシーンでの文法エラー不発生をテスト"""
    mock_adapter = MockLLMAdapterForProseRefinement()
    mock_llm_service = LLMService()
    mock_llm_service.adapter = mock_adapter
    
    agent = ProseRefinerAgent(llm_service=mock_llm_service)
    
    test_text = "彼は剣を振り下ろした。敵は驚いていた。" 
    result = await agent.refine(test_text, genre="fantasy_action", scene_type="action")
    
    assert isinstance(result, ProseRefineResult)
    assert result.refined_text is not None
    assert len(result.refined_text) > 0
    
    refined = result.refined_text
    assert refined.endswith("。") or refined.endswith("!") or refined.endswith("？") or len(refined) == 0, \
        f"文が適切に終わっていない: {repr(refined)}"
    assert not refined.startswith("、") and not refined.startswith("　"), \
        f"不自然な開始（主語欠落の可能性）: {repr(refined)}"


@pytest.mark.asyncio
async def test_prose_refiner_empty_and_edge_cases():
    """空文字列や端値ケースのテスト"""
    mock_adapter = MockLLMAdapterForProseRefinement()
    mock_llm_service = LLMService()
    mock_llm_service.adapter = mock_adapter
    
    agent = ProseRefinerAgent(llm_service=mock_llm_service)
    
    result_empty = await agent.refine("", genre="fantasy_action")
    assert isinstance(result_empty, ProseRefineResult)
    assert result_empty.refined_text == ""
    assert result_empty.total_fixes_count == 0
    
    result_whitespace = await agent.refine("   \n\t   ", genre="fantasy_action")
    assert isinstance(result_whitespace, ProseRefineResult)
    assert isinstance(result_whitespace.refined_text, str)
    
    result_short = await agent.refine("あ", genre="fantasy_action")
    assert isinstance(result_short, ProseRefineResult)
    assert isinstance(result_short.refined_text, str)
