import pytest
from pydantic import ValidationError
from src.backend.routers.orchestrated import OrchestratedGenerateRequest, OrchestratedGenerateResponse

def test_orchestrated_request_valid():
    req = OrchestratedGenerateRequest(
        book_id=1,
        branch_id=1,
        ep_num=1,
        title="テスト小説",
        target_word_count=3000
    )
    assert req.book_id == 1
    assert req.ep_num == 1
    assert req.target_word_count == 3000

def test_orchestrated_response_model():
    res = OrchestratedGenerateResponse(
        task_id="task_abc_123",
        status="running",
        message="執筆パイプラインを開始しました"
    )
    assert res.task_id == "task_abc_123"
    assert res.status == "running"