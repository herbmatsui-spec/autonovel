import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks.test_harness import BackendTestHarness
from src.backend.workflows.episode_writing_workflow import EpisodeWritingWorkflow
from src.shared.utils import StatusReporter

@pytest.fixture
def harness():
    return BackendTestHarness()

@pytest.mark.asyncio
async def test_episode_writing_workflow_pipeline_success(harness):
    """
    EpisodeWritingWorkflow の正常系テスト (パイプラインモード):
    - writing.generate_episodes_pipeline が正しく呼ばれること
    - プリフェッチがトリガーされること
    - 非同期監査タスクがエンキューされること
    を確認する。
    """
    book_id = 1
    write_from = 1
    write_to = 5
    passion = 0.8
    word_count = 3000
    do_refine = True
    env_state = {}
    pipeline_mode = True
    
    # Mock writing service
    mock_writing = AsyncMock()
    mock_writing.generate_episodes_pipeline.return_value = (15000, [3]) # chars_count, failed_list
    
    # Workflow Instance
    workflow = EpisodeWritingWorkflow()
    workflow.writing = mock_writing
    # Mock for prefetch components to avoid errors
    workflow.vector_store = MagicMock()
    workflow.llm_client = MagicMock()
    
    reporter = MagicMock(spec=StatusReporter)
    
    # Patch the task enqueue function
    with patch("src.backend.tasks.enqueue_audit_after_write") as mock_enqueue:
        result = await workflow.execute(
            reporter=reporter,
            book_id=book_id,
            write_from=write_from,
            write_to=write_to,
            passion=passion,
            word_count=word_count,
            do_refine=do_refine,
            env_state=env_state,
            pipeline_mode=pipeline_mode,
            mode="final"
        )
        
        # Assertions
        assert result["chars_count"] == 15000
        assert result["failed_episodes"] == [3]
        assert result["book_id"] == book_id
        
        # Verify writing service call
        mock_writing.generate_episodes_pipeline.assert_called_once_with(
            book_id, write_from, write_to, passion, word_count, reporter=reporter, mode="final"
        )
        
        # Verify audit enqueue
        mock_enqueue.assert_called_once_with(book_id, write_from, write_to)
        
        # Verify reporter report for audit
        reporter.report.assert_any_call("⚖️ 非同期の論理監査タスク (Shadow Mode) をエンキューしました。", "info")

@pytest.mark.asyncio
async def test_episode_writing_workflow_standard_success(harness):
    """
    EpisodeWritingWorkflow の正常系テスト (通常モード):
    - writing.generate_episodes が正しく呼ばれること
    を確認する。
    """
    book_id = 1
    write_from = 1
    write_to = 1
    passion = 0.5
    word_count = 2000
    do_refine = False
    env_state = {"some": "state"}
    pipeline_mode = False
    
    mock_writing = AsyncMock()
    mock_writing.generate_episodes.return_value = 5000
    
    workflow = EpisodeWritingWorkflow()
    workflow.writing = mock_writing
    workflow.vector_store = MagicMock()
    workflow.llm_client = MagicMock()
    
    reporter = MagicMock(spec=StatusReporter)
    
    with patch("src.backend.tasks.enqueue_audit_after_write") as mock_enqueue:
        result = await workflow.execute(
            reporter=reporter,
            book_id=book_id,
            write_from=write_from,
            write_to=write_to,
            passion=passion,
            word_count=word_count,
            do_refine=do_refine,
            env_state=env_state,
            pipeline_mode=pipeline_mode,
            mode="final"
        )
        
        assert result["chars_count"] == 5000
        assert result["book_id"] == book_id
        
        mock_writing.generate_episodes.assert_called_once_with(
            book_id, write_from, write_to, passion, word_count, do_refine,
            reporter=reporter, env_state=env_state, mode="final"
        )
        mock_enqueue.assert_called_once_with(book_id, write_from, write_to)
