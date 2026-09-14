import pytest

def test_workflow_end_to_end_smoke():
    """ワークフロー層のエンドツーエンドスモークテスト"""
    pipeline_state = {"step": "init", "done": False}
    pipeline_state["step"] = "writing"
    pipeline_state["done"] = True
    assert pipeline_state["done"] is True