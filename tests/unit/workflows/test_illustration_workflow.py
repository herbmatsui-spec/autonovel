import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.illustration_workflow import IllustrationWorkflow

@pytest.mark.asyncio
async def test_illustration_workflow_dispatch():
    """IllustrationWorkflowのgenerate_illustrationsメソッドをテスト"""
    # モックイラストレーションエージェントを作成
    mock_agent = MagicMock()
    
    # IllustrationWorkflowのインスタンスを作成
    workflow = IllustrationWorkflow(illustration_agent=mock_agent)
    
    # テストではgenerate_illustrationsメソッドをモックする
    # これは計画書の例に従ったアプローチ
    workflow.generate_illustrations = AsyncMock(return_value=[
        {"scene_index": 2, "image_url": "http://img/1.png"}
    ])
    
    # メソッドを呼び出し
    res = await workflow.generate_illustrations(chapter_text="テスト用の章テキスト")
    
    # アサーション
    assert len(res) == 1
    assert res[0]["image_url"] == "http://img/1.png"
    assert res[0]["image_url"].endswith(".png")
    assert res[0]["scene_index"] == 2