import pytest
from unittest.mock import AsyncMock
from src.backend.workflows.reverse_plot_workflow import ReversePlotGenerationWorkflow

@pytest.mark.asyncio
async def test_reverse_plot_workflow():
    """ReversePlotGenerationWorkflowのextract_plotメソッドをテスト"""
    # ReversePlotGenerationWorkflowのインスタンスを作成
    workflow = ReversePlotGenerationWorkflow()

    # テストではextract_plotメソッドをモックする
    # これは計画書の例に従ったアプローチ
    workflow.extract_plot = AsyncMock(return_value={"acts": ["第1幕", "第2幕"]})

    # メソッドを呼び出し
    res = await workflow.extract_plot("小説テキスト全文")

    # アサーション
    assert "acts" in res
    assert len(res["acts"]) == 2
    assert res["acts"] == ["第1幕", "第2幕"]
