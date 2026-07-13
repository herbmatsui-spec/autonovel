from src.backend.sanitizer import OutputSanitizer


def test_extract_json():
    # Test normal JSON
    json_str = '{"key": "value"}'
    assert OutputSanitizer.parse_llm_json(json_str) == {"key": "value"}

    # Test Markdown JSON
    md_json = '```json\n{"key": "value"}\n```'
    assert OutputSanitizer.parse_llm_json(md_json) == {"key": "value"}

    # Test JSON with prefix/suffix
    dirty_json = 'Here is the response:\n```\n{"key": "value"}\n```\nHope it helps.'
    assert OutputSanitizer.parse_llm_json(dirty_json) == {"key": "value"}

    # Test invalid JSON
    invalid_json = 'This is not json'
    assert OutputSanitizer.parse_llm_json(invalid_json) == {}

def test_sanitize_metadata():
    # Test valid metadata
    meta = {
        "title": "Title",
        "synopsis": "Synopsis",
        "characters": ["Char 1"],
        "world_rules": ["Rule 1"]
    }
    sanitized = OutputSanitizer.normalize_metadata(meta)
    assert sanitized == meta

    # Test missing fields
    partial_meta = {"title": "Title"}
    sanitized = OutputSanitizer.normalize_metadata(partial_meta)
    assert "synopsis" not in sanitized # normalizer doesn't add it unless it's a specific wrapper

    # Test incorrect types
    bad_type_meta = {
        "title": 123,
        "characters": "not a list",
        "world_rules": "not a list either"
    }
    sanitized = OutputSanitizer.normalize_metadata(bad_type_meta)
    assert sanitized["title"] == "123"

def test_clean_text():
    # Test removing meta statements
    text = "[METADATA_JSON]"
    assert OutputSanitizer._clean_story(text).strip() == ""

    # Test stripping whitespace
    text = "  Hello World  \n  "
    assert OutputSanitizer._clean_story(text).strip() == "Hello World"
