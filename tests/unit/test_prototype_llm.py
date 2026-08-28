"""
tests/unit/test_prototype_llm.py - ステップ 3: GatewayLLMGenerator の単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.prototype.llm_adapter import GatewayLLMGenerator


@pytest.mark.asyncio
async def test_gateway_llm_generator_async():
    """モックゲートウェイを用いた非同期生成テスト"""
    mock_gateway = MagicMock()
    mock_res = MagicMock()
    mock_res.story_content = "第1話の生成本文テストです。"
    mock_gateway.generate_text = AsyncMock(return_value=mock_res)

    generator = GatewayLLMGenerator(llm_gateway=mock_gateway)
    text = await generator.agenerate("プロット指示", target_chars=500, part_id=1, ep=1)

    assert text == "第1話の生成本文テストです。"
    mock_gateway.generate_text.assert_called_once()


def test_gateway_llm_generator_sync_mock():
    """同期インターフェース呼び出しテスト"""
    mock_gateway = MagicMock()
    mock_res = MagicMock()
    mock_res.story_content = "同期生成された本文。"
    mock_gateway.generate_text = AsyncMock(return_value=mock_res)

    generator = GatewayLLMGenerator(llm_gateway=mock_gateway)
    text = generator.generate("プロット指示", target_chars=500, part_id=1, ep=1)

    assert text == "同期生成された本文。"


def test_gateway_llm_generator_fallback():
    """フォールバック（MockLLMGenerator）動作テスト"""
    generator = GatewayLLMGenerator(llm_gateway=None, world_data={"symbol": "光の結晶"})
    text = generator.generate("プロット", target_chars=200, part_id=1, ep=1)
    assert isinstance(text, str)
    assert len(text) > 0
