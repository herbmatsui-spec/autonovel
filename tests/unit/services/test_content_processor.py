import pytest
from src.services.content_processor import ContentProcessor

def test_sanitize():
    processor = ContentProcessor()
    assert processor.sanitize("") == ""
    assert processor.sanitize("hello") == "hello"
    assert processor.sanitize("hello\nworld") == "hello\nworld"

def test_apply_tone():
    processor = ContentProcessor()
    assert processor.apply_tone("", "cheerful") == ""
    assert processor.apply_tone("hello", "cheerful") == "hello"
    assert processor.apply_tone("hello\nworld", "serious") == "hello\nworld"
    # tone is ignored, but we can still pass any string