import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.orchestrator import DocumentOrchestrator, ProcessingResult
from src.config.config import Config

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.gemini_api_key = "test_api_key"
    config.google_api_key = "test_api_key"
    config.pdf_dpi = 200
    config.output_directory = Path("manual_processor/output")
    config.output_directory.mkdir(parents=True, exist_ok=True)
    return config

@pytest.fixture
def orchestrator(mock_config):
    return DocumentOrchestrator(config=mock_config)

def test_orchestrator_process_file_success(orchestrator):
    with patch.object(orchestrator.processor, 'process_pdf') as mock_process:
        mock_process.return_value = {
            "success": True,
            "extracted_text": "Mock extracted text",
            "summary": "Mock summary",
            "key_points": ["Point 1", "Point 2"],
            "sections": {"Intro": "Intro text"},
            "output_files": {"pdf": "out.pdf"}
        }
        
        test_file = Path("test_doc.pdf")
        test_file.touch()
        try:
            result = orchestrator.process_file(test_file)
            assert result.success is True
            assert "Successfully processed" in result.message
        finally:
            test_file.unlink()

def test_orchestrator_process_file_failure(orchestrator):
    with patch.object(orchestrator.processor, 'process_pdf') as mock_process:
        mock_process.return_value = {"success": False, "error": "OCR failed"}
        test_file = Path("test_fail.pdf")
        test_file.touch()
        try:
            result = orchestrator.process_file(test_file)
            assert result.success is False
            assert "OCR failed" in result.message
        finally:
            test_file.unlink()

def test_orchestrator_worker_loop(orchestrator):
    with patch.object(orchestrator.processor, 'process_pdf') as mock_process:
        mock_process.return_value = {"success": True, "summary": "Async summary"}
        test_file = Path("async_test.pdf")
        test_file.touch()
        try:
            orchestrator.start()
            orchestrator.add_file_to_queue(test_file)
            result = orchestrator.get_result(timeout=2.0)
            assert result is not None
            assert result.success is True
            orchestrator.stop()
        finally:
            test_file.unlink()

def test_orchestrator_invalid_file_path(orchestrator):
    with patch.object(orchestrator.processor, 'process_pdf', side_effect=FileNotFoundError("File not found")):
        test_file = Path("non_existent.pdf")
        result = orchestrator.process_file(test_file)
        assert result.success is False
        assert "Error processing" in result.message

def test_orchestrator_status_tracking(orchestrator):
    assert orchestrator.status == "idle"
    
    with patch.object(orchestrator.processor, 'process_pdf') as mock_process:
        mock_process.return_value = {"success": True}
        test_file = Path("status_test.pdf")
        test_file.touch()
        try:
            orchestrator.process_file(test_file)
            assert len(orchestrator.processed_files) == 1
            assert orchestrator.get_status()["processed_count"] == 1
        finally:
            test_file.unlink()

def test_orchestrator_rapid_start_stop(orchestrator):
    orchestrator.start()
    orchestrator.stop()
    orchestrator.start()
    orchestrator.stop()
    assert orchestrator.worker_thread is not None

def test_orchestrator_queue_empty_get_result(orchestrator):
    result = orchestrator.get_result(timeout=0.1)
    assert result is None

def test_orchestrator_multiple_files_queue(orchestrator):
    with patch.object(orchestrator.processor, 'process_pdf') as mock_process:
        mock_process.return_value = {"success": True}
        files = [Path(f"test_{i}.pdf") for i in range(3)]
        for f in files: f.touch()
        
        try:
            orchestrator.start()
            for f in files:
                orchestrator.add_file_to_queue(f)
            
            results = []
            for _ in range(3):
                res = orchestrator.get_result(timeout=2.0)
                if res: results.append(res)
            
            assert len(results) == 3
            assert all(r.success for r in results)
            orchestrator.stop()
        finally:
            for f in files: f.unlink()
