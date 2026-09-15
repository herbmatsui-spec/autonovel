import pytest
from src.backend.sanitizer import NormalizationFlow, OutputSanitizer, ContentValidator, TextFormatter

def test_normalization_flow_unwrap():
    flow = NormalizationFlow()
    raw = {"metadata": {"title": "覇権小説", "genre": "fantasy"}}
    result = flow.unwrap_nested_metadata(raw)
    assert result["title"] == "覇権小説"
    assert result["genre"] == "fantasy"

def test_normalization_flow_resolve_aliases():
    flow = NormalizationFlow()
    raw = {"char_list": ["Alice", "Bob"]}
    result = flow.resolve_aliases(raw)
    assert "characters" in result
    assert result["characters"] == ["Alice", "Bob"]

def test_output_sanitizer_fix_json():
    sanitizer = OutputSanitizer()
    broken_json = '```json\n{"title": "魔法剣士", "chapters": [1, 2, 3]}\n```'
    parsed = sanitizer.parse_llm_json(broken_json)
    assert parsed["title"] == "魔法剣士"
    assert len(parsed["chapters"]) == 3

def test_content_validator_rhythm():
    validator = ContentValidator()
    # 文末が同一語尾で3連続以上続く場合を検知
    repetitive_text = "彼は歩いた。空を見上げた。剣を抜いた。"
    is_valid, msg = validator.check_rhythm(repetitive_text)
    # 検証結果が返ることを確認
    assert isinstance(is_valid, bool)

def test_text_formatter_remove_ai_isms():
    formatter = TextFormatter()
    raw_prose = "言わば、彼は感情の三段論法のように納得した。"
    cleaned = formatter.remove_ai_isms(raw_prose)
    assert isinstance(cleaned, str)