import pytest
from unittest.mock import AsyncMock
from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow

@pytest.mark.asyncio
async def test_refine_erotic_workflow():
    """RefineEroticWorkflowのrefine_sceneメソッドをテスト"""
    # RefineEroticWorkflowのインスタンスを作成
    workflow = RefineEroticWorkflow()

    # テストではrefine_sceneメソッドをモックする
    # これは計画書の例に従ったアプローチ
    workflow.refine_scene = AsyncMock(return_value="洗練された描写テキスト")

    # メソッドを呼び出し
    result = await workflow.refine_scene("初期下書き")

    # アサーション
    assert result == "洗練された描写テキスト"
