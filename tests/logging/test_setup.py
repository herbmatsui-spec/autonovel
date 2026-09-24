import json
import sys
from io import StringIO
from unittest.mock import patch
from loguru import logger
from src.logging.setup import setup_logging

def test_logs_are_json():
    # Capture stdout since setup_logging outputs to stdout
    mock_stdout = StringIO()
    with patch("sys.stdout", mock_stdout):
        # Reset logger to clean state
        logger.remove()
        # Initialize logging (outputs to our mocked stdout)
        setup_logging()
        # Log a test message
        logger.info("Test message", key="value")
        
        # Get the output
        output = mock_stdout.getvalue().strip()
        # The output should be a JSON string
        try:
            log_entry = json.loads(output)
        except json.JSONDecodeError:
            raise AssertionError(f"Log output is not valid JSON: {output}")
        
        # Check the content in the record field
        record = log_entry["record"]
        assert record["message"] == "Test message"
        assert record["extra"]["key"] == "value"
        assert record["level"]["name"] == "INFO"