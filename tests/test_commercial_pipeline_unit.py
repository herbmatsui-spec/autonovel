"""
Unit Tests for CommercialPipeline Error Handling and Retry Logic
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from typing import Dict, List, Any
from src.backend.workflows.commercial_pipeline import CommercialPipeline, PipelineError

@pytest.mark.asyncio
async def test_pipeline_retry_decorator_success():
    """retry_decorator should succeed on first attempt without retrying"""
    pipeline = CommercialPipeline()
    call_count = 0
    
    async def mock_successful_call(bible: Dict[str, Any], samples: List[Dict[str, Any]], platforms: List[str]):
        nonlocal call_count
        call_count += 1
        return [], {}
    
    with patch.object(pipeline, '_generate_content_async', new=mock_successful_call):
        result = await pipeline._generate_content_async({}, [], ["kakuyomu"])
        assert result == ([], {})
        assert call_count == 1, "Function should have been called only once"

@pytest.mark.asyncio
async def test_pipeline_retry_decorator_exceeds_attempts():
    """retry_decorator should raise PipelineError after max attempts"""
    pipeline = CommercialPipeline()
    
    async def mock_failing_call(bible: Dict[str, Any], samples: List[Dict[str, Any]], platforms: List[str]):
        raise RuntimeError("Transient error")
    
    with patch.object(pipeline, '_generate_content_async', new=mock_failing_call):
        with pytest.raises(PipelineError, match="Pipeline step failed after 3 attempts"):
            await pipeline._generate_content_async({}, [], ["kakuyomu"])

@pytest.mark.asyncio
async def test_step_plan_invalid_config():
    """_step_plan should raise PipelineError for malformed config"""
    pipeline = CommercialPipeline()
    invalid_config = {}
    
    with pytest.raises(PipelineError, match="Bible generation failed"):
        await pipeline._step_plan_async(invalid_config)

@pytest.mark.asyncio
async def test_csv_schedule_creation():
    """_create_schedule_csv should produce valid CSV content"""
    pipeline = CommercialPipeline()
    exports = {
        "kakuyomu": [
            {"ep_num": 1, "title": "第1話", "format": "web", "target_word_count": 1500}
        ],
        "naru": [
            {"ep_num": 1, "title": "第1話", "format": "web", "target_word_count": 1500}
        ]
    }
    
    csv_path = pipeline._create_schedule_csv(exports)
    assert csv_path == "/tmp/commercial_schedule.csv"
    
    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "platform,ep_num,title,format,target_word_count,output_path" in content
    assert "kakuyomu,1,第1話,web,1500,/output/kakuyomu_ep1.txt" in content

@pytest.mark.asyncio
async def test_run_handles_pipeline_error_gracefully():
    """run should catch PipelineError and return error dict"""
    pipeline = CommercialPipeline()
    
    with patch.object(pipeline, "run", new_value=PipelineError("Test error")):
        result = await pipeline.run({}, [], ["kakuyomu"])
        assert result["error"] == "Test error"
        assert result["selected"] == []
        assert result["exports"] == {}
        assert result["schedule_csv"] is None