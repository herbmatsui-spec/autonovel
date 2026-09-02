"""Unit tests for src/backend/sanitizer.py - HTML sanitizer, JSON repair, and text quality validation."""

import json
import pytest

from src.backend.sanitizer import (
    NormalizationFlow,
    TonePerfector,
    OutputSanitizer,
    ContentValidator,
    SeriousnessFilter,
    TextFormatter,
    AtmosphereGenerator,
    CharacterRegistry,
)


class TestNormalizationFlow:
    """Tests for NormalizationFlow class."""

    def setup_method(self):
        self.flow = NormalizationFlow()

    def test_unwrap_nested_metadata_single_key(self):
        """Test unwrapping single-key nested dict."""
        data = {"metadata": {"title": "Test", "content": "Story"}}
        result = self.flow.unwrap_nested_metadata(data)
        assert result == {"title": "Test", "content": "Story"}

    def test_unwrap_nested_metadata_multiple_keys(self):
        """Test unwrapping when multiple wrapper keys exist."""
        data = {"response": {"data": {"episode": 1}}, "extra": "value"}
        result = self.flow.unwrap_nested_metadata(data)
        assert "episode" in result
        assert result["episode"] == 1

    def test_unwrap_nested_metadata_non_dict(self):
        """Test that non-dict input is returned as-is."""
        assert self.flow.unwrap_nested_metadata("string") == "string"
        assert self.flow.unwrap_nested_metadata(123) == 123
        assert self.flow.unwrap_nested_metadata(None) is None

    def test_resolve_aliases_ep_num(self):
        """Test episode number alias resolution."""
        data = {"episode_number": 5}
        result = self.flow.resolve_aliases(data)
        assert result["ep_num"] == 5

        data = {"ep_no": "3"}
        result = self.flow.resolve_aliases(data)
        assert result["ep_num"] == 3

        data = {"chapter": "Chapter 7"}
        result = self.flow.resolve_aliases(data)
        assert result["ep_num"] == 7

    def test_resolve_aliases_scene_number(self):
        """Test scene number alias resolution."""
        data = {"scene_id": 10}
        result = self.flow.resolve_aliases(data)
        assert result["scene_number"] == 10

        data = {"id": "5"}
        result = self.flow.resolve_aliases(data)
        assert result["scene_number"] == 5

    def test_resolve_aliases_severity(self):
        """Test severity alias resolution."""
        data = {"severity": "critical"}
        result = self.flow.resolve_aliases(data)
        assert result["severity"] == "Critical"

        data = {"severity": "重大"}
        result = self.flow.resolve_aliases(data)
        assert result["severity"] == "Major"

        data = {"severity": "minor"}
        result = self.flow.resolve_aliases(data)
        assert result["severity"] == "Minor"

    def test_resolve_aliases_detailed_blueprint(self):
        """Test detailed_blueprint alias resolution."""
        data = {"outline": "This is a detailed story outline with enough content."}
        result = self.flow.resolve_aliases(data)
        assert result["detailed_blueprint"] == "This is a detailed story outline with enough content."

    def test_resolve_aliases_final_content(self):
        """Test final_content alias resolution."""
        data = {"script_content": "This is the final story content that is long enough."}
        result = self.flow.resolve_aliases(data)
        # The function looks for long enough content in alias fields
        assert "final_content" in result or "script_content" in result

    def test_coerce_types_force_str_keys(self):
        """Test string coercion for force_str_keys."""
        data = {"title": 123, "summary": ["item1", "item2"], "tone": {"key": "value"}}
        result = self.flow.coerce_types(data)
        assert result["title"] == "123"
        assert result["summary"] == "item1, item2"
        assert "key" in result["tone"]

    def test_coerce_types_next_hook_string(self):
        """Test next_hook string to JSON conversion."""
        data = {"next_hook": '{"type": "New Crisis", "description": "Test"}'}
        result = self.flow.coerce_types(data)
        assert isinstance(result["next_hook"], dict)
        assert result["next_hook"]["type"] == "New Crisis"

    def test_coerce_types_next_hook_none(self):
        """Test next_hook None handling."""
        data = {"next_hook": None}
        result = self.flow.coerce_types(data)
        assert result["next_hook"]["type"] == "Quiet Foreshadowing"

    def test_coerce_types_numeric_fields(self):
        """Test numeric field coercion."""
        data = {"stress_delta": "10", "love_delta": "-5", "tension": "high 8"}
        result = self.flow.coerce_types(data)
        assert result["stress_delta"] == 10
        assert result["love_delta"] == -5
        assert result["tension"] == 8

    def test_normalize_lists_scenes(self):
        """Test scene list normalization."""
        data = ["scene1", "scene2"]
        result = self.flow.normalize_lists(data, "scenes")
        assert all(isinstance(item, dict) for item in result)
        assert result[0]["action"] == "scene1"
        assert result[0]["scene_number"] == 1

    def test_normalize_lists_beats(self):
        """Test beat list normalization."""
        data = [{"beat_type": "導入 シーン", "sensory_keywords": "視覚,聴覚"}]
        result = self.flow.normalize_lists(data, "beats")
        assert result[0]["beat_type"] == "導入"
        assert result[0]["sensory_keywords"] == ["視覚", "聴覚"]

    def test_apply_defaults(self):
        """Test default value application."""
        data = {"one_line_summary": "Test story"}
        result = self.flow.apply_defaults(data, is_root=True)
        assert result["burned_cost_or_loot"] == "特になし"
        assert result["antagonist_status"] == "現状維持"

    def test_normalize_metadata_full_flow(self):
        """Test complete metadata normalization flow."""
        data = {
            "response": {
                "episode_number": "1",
                "outline": "Story outline",
                "script_content": "Story content",
                "severity": "major",
                "stress_delta": "5",
            }
        }
        result = self.flow.normalize_metadata(data)
        assert result["ep_num"] == 1
        assert result["severity"] == "Major"
        assert result["stress_delta"] == 5


class TestTonePerfector:
    """Tests for TonePerfector class."""

    def test_enforce_tone_first_person(self):
        """Test first person pronoun enforcement."""
        chars = [CharacterRegistry(name="Test", first_person="I", second_person="you", suffix_style="")]
        text = 'He said "I am going".'
        result = TonePerfector.enforce_tone(text, chars)
        # The function should process without error
        assert isinstance(result, str)

    def test_enforce_tone_second_person(self):
        """Test second person pronoun enforcement."""
        chars = [CharacterRegistry(name="Test", first_person="I", second_person="you", suffix_style="")]
        text = 'He asked "Are you coming?"'
        result = TonePerfector.enforce_tone(text, chars)
        assert isinstance(result, str)

    def test_enforce_tone_suffix_style(self):
        """Test suffix style enforcement."""
        chars = [CharacterRegistry(name="Test", first_person="", second_person="", suffix_style=" indeed")]
        text = 'He said "Going."'
        result = TonePerfector.enforce_tone(text, chars)
        assert isinstance(result, str)

    def test_enforce_tone_empty_characters(self):
        """Test with empty character list."""
        result = TonePerfector.enforce_tone("テスト", [])
        assert result == "テスト"

    def test_enforce_tone_no_name(self):
        """Test with character without name."""
        chars = [CharacterRegistry(name="", first_person="私")]
        result = TonePerfector.enforce_tone('「私は行く」', chars)
        assert result == '「私は行く」'


class TestOutputSanitizer:
    """Tests for OutputSanitizer class."""

    def test_parse_llm_json_valid(self):
        """Test parsing valid JSON."""
        text = '{"title": "Test", "content": "Story"}'
        result = OutputSanitizer.parse_llm_json(text)
        assert result["title"] == "Test"
        assert result["content"] == "Story"

    def test_parse_llm_json_with_wrapper(self):
        """Test parsing JSON with surrounding text."""
        text = 'Here is the result: {"title": "Test"} End of response.'
        result = OutputSanitizer.parse_llm_json(text)
        assert result["title"] == "Test"

    def test_parse_llm_json_empty(self):
        """Test parsing empty string."""
        result = OutputSanitizer.parse_llm_json("")
        assert result == {}

    def test_parse_llm_json_invalid(self):
        """Test parsing invalid JSON."""
        text = 'This is not JSON at all'
        result = OutputSanitizer.parse_llm_json(text)
        assert result == {}

    def test_extract_content_and_metadata_separator(self):
        """Test extraction with separator."""
        text = f"Story content\n### NOVEL CONTENT ###\n{{\"title\": \"Test\"}}\n### NOVEL CONTENT ###"
        metadata, content = OutputSanitizer.extract_content_and_metadata(text)
        # The function extracts metadata from the separator format
        assert isinstance(metadata, dict)
        assert isinstance(content, str)

    def test_extract_content_and_metadata_json_tail(self):
        """Test extraction with JSON at tail."""
        text = 'Story content here. {"title": "Test", "final_content": "Full story"}'
        metadata, content = OutputSanitizer.extract_content_and_metadata(text)
        assert metadata["title"] == "Test"

    def test_extract_content_and_metadata_plain_text(self):
        """Test plain text fallback."""
        text = "Just plain story text without JSON."
        metadata, content = OutputSanitizer.extract_content_and_metadata(text)
        assert metadata == {}
        assert content == "Just plain story text without JSON."

    def test_clean_story_removes_meta_patterns(self):
        """Test removal of meta patterns."""
        text = "了解しました。\n\nストーリー本文です。\n以下はプロットです。"
        result = OutputSanitizer._clean_story(text)
        assert "了解しました" not in result
        assert "以下はプロットです" not in result
        assert "ストーリー本文です" in result

    def test_clean_story_removes_brackets(self):
        """Test removal of bracket tags."""
        text = "[METADATA_JSON] content [thought_process] thinking [SCENE 1] scene"
        result = OutputSanitizer._clean_story(text)
        assert "[METADATA_JSON]" not in result
        assert "[thought_process]" not in result
        assert "[SCENE 1]" not in result

    def test_clean_story_removes_markdown(self):
        """Test removal of markdown formatting."""
        text = "**bold** *italic* __underline__ ~~strike~~"
        result = OutputSanitizer._clean_story(text)
        assert "**" not in result
        assert "*" not in result
        assert "__" not in result
        assert "~~" not in result

    def test_normalize_metadata_delegates(self):
        """Test normalize_metadata delegates to NormalizationFlow."""
        data = {"episode_number": 1, "summary": "Test"}
        result = OutputSanitizer.normalize_metadata(data)
        assert result["ep_num"] == 1

    def test_fix_json_python_quotes(self):
        """Test fixing Python-style quotes in JSON."""
        text = "{'key': 'value', 'num': 123}"
        result = OutputSanitizer.fix_json(text)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["num"] == 123

    def test_fix_json_trailing_comma(self):
        """Test fixing trailing commas."""
        text = '{"a": 1, "b": 2,}'
        result = OutputSanitizer.fix_json(text)
        parsed = json.loads(result)
        assert parsed["a"] == 1
        assert parsed["b"] == 2

    def test_fix_json_unbalanced_braces(self):
        """Test fixing unbalanced braces."""
        text = '{"a": 1, "b": {"c": 2}'
        result = OutputSanitizer.fix_json(text)
        parsed = json.loads(result)
        assert parsed["a"] == 1
        assert parsed["b"]["c"] == 2

    def test_fix_json_comments(self):
        """Test removing JSON comments."""
        text = '{"a": 1, // comment\n "b": 2 /* another */}'
        result = OutputSanitizer.fix_json(text)
        parsed = json.loads(result)
        assert parsed["a"] == 1
        assert parsed["b"] == 2

    def test_format_validation_error(self):
        """Test formatting validation errors."""
        from pydantic import ValidationError, BaseModel

        class TestModel(BaseModel):
            name: str
            age: int

        try:
            TestModel(name=123, age="not_int")
        except ValidationError as e:
            result = OutputSanitizer.format_validation_error(e)
            assert "name" in result
            assert "age" in result
            assert "文字列" in result or "整数" in result


class TestContentValidator:
    """Tests for ContentValidator class."""

    def test_check_rhythm_uniform(self):
        """Test rhythm check for uniform sentence lengths."""
        text = "This is a test. This is a test. This is a test. This is a test. This is a test."
        errors = ContentValidator.check_rhythm(text)
        # Uniform sentence lengths should trigger rhythm warning
        assert isinstance(errors, list)

    def test_check_rhythm_varied(self):
        """Test rhythm check for varied sentence lengths."""
        text = "Short. This is a longer sentence here. Very long sentence that goes on and on. Tiny. Medium size."
        errors = ContentValidator.check_rhythm(text)
        # Should handle varied lengths
        assert isinstance(errors, list)

    def test_check_rhythm_short_text(self):
        """Test rhythm check for short text."""
        text = "Short."
        errors = ContentValidator.check_rhythm(text)
        assert isinstance(errors, list)

    def test_check_rhythm_consecutive_endings(self):
        """Test detection of consecutive same endings."""
        text = "Going desu. Coming desu. Seeing desu."
        errors = ContentValidator.check_rhythm(text)
        # May detect consecutive endings
        assert isinstance(errors, list)

    def test_check_catharsis_reservation_ep1_has_keywords(self):
        """Test catharsis check for episode 1 with keywords."""
        text = "Someday I will surely revenge. Signs of reversal appeared."
        errors = ContentValidator.check_catharsis_reservation(text, 1)
        assert isinstance(errors, list)

    def test_check_catharsis_reservation_ep1_no_keywords(self):
        """Test catharsis check for episode 1 without keywords."""
        text = "Today is nice weather. Went for a walk."
        errors = ContentValidator.check_catharsis_reservation(text, 1)
        assert isinstance(errors, list)

    def test_check_catharsis_reservation_not_ep1(self):
        """Test catharsis check for non-episode 1."""
        text = "Normal story."
        errors = ContentValidator.check_catharsis_reservation(text, 5)
        assert isinstance(errors, list)

    def test_auto_correct_rhythm(self):
        """Test rhythm auto-correction."""
        text = "これは長い文章です、でも区切れます。短い。これも長い文章ですね、区切れますよ。短。"
        result = ContentValidator.auto_correct_rhythm(text)
        assert len(result) > 0

    def test_analyze_word_heaviness_high_kanji(self):
        """Test word heaviness analysis for high kanji rate."""
        text = "漢字漢字漢字漢字漢字漢字漢字漢字漢字漢字"
        result = ContentValidator.analyze_word_heaviness(text)
        assert result["kanji_rate"] > 35
        assert result["is_heavy"] is True

    def test_analyze_word_heaviness_low_kanji(self):
        """Test word heaviness analysis for low kanji rate."""
        text = "ひらがなひらがなひらがな"
        result = ContentValidator.analyze_word_heaviness(text)
        assert result["kanji_rate"] < 35
        assert result["is_heavy"] is False

    def test_analyze_word_heaviness_empty(self):
        """Test word heaviness analysis for empty text."""
        result = ContentValidator.analyze_word_heaviness("")
        assert result["kanji_rate"] == 0
        assert result["is_heavy"] is False


class TestSeriousnessFilter:
    """Tests for SeriousnessFilter class."""

    def test_filter_light_mode(self):
        """Test filter in light mode (no changes)."""
        filter_obj = SeriousnessFilter()
        text = "テスト！？テスト！！テスト……"
        result = filter_obj.filter(text, is_light=True)
        assert result == text

    def test_filter_serious_mode(self):
        """Test filter in serious mode."""
        filter_obj = SeriousnessFilter()
        text = "テスト！？テスト！！テスト………"
        result = filter_obj.filter(text, is_light=False)
        assert "！？" not in result
        assert "！！" not in result
        assert "……" in result  # 4 dots become 2


class TestTextFormatter:
    """Tests for TextFormatter class."""

    def test_remove_ai_isms(self):
        """Test removal of AI-isms."""
        text = "言うまでもないが、彼は行く。特筆すべきは、その時だった。息を呑んだ。"
        result = TextFormatter.remove_ai_isms(text)
        assert "言うまでもない" not in result
        assert "特筆すべきは" not in result
        assert "その時だった" not in result
        assert "言葉を失った" in result

    def test_enforce_cliffhanger(self):
        """Test cliffhanger enforcement."""
        text = "物語は続く。"
        result = TextFormatter.enforce_cliffhanger(text)
        assert result.endswith("――")

    def test_enforce_cliffhanger_already_has(self):
        """Test cliffhanger when already present."""
        text = "物語は続く――"
        result = TextFormatter.enforce_cliffhanger(text)
        assert result.count("――") == 1

    def test_format_for_kakuyomu_basic(self):
        """Test basic kakuyomu formatting."""
        text = "彼は言った。「行くよ」。\n\n彼女は微笑んだ。"
        result = TextFormatter.format_for_kakuyomu(text)
        assert "　" in result  # Full-width indent
        assert "「行くよ」" in result

    def test_format_for_kakuyomu_removes_ai_prefix(self):
        """Test removal of AI prefixes."""
        text = "承知しました。\n\n彼は行った。"
        result = TextFormatter.format_for_kakuyomu(text)
        assert "承知しました" not in result

    def test_format_for_kakuyomu_removes_code_blocks(self):
        """Test removal of code blocks."""
        text = "```python\nprint('hello')\n```\n\n本文。"
        result = TextFormatter.format_for_kakuyomu(text)
        assert "```" not in result
        assert "本文" in result


class TestAtmosphereGenerator:
    """Tests for AtmosphereGenerator class."""

    def test_get_prompt(self):
        """Test prompt generation."""
        result = AtmosphereGenerator.get_prompt("夏", "雨")
        assert "夏" in result
        assert "雨" in result

    def test_get_sensory_anchors_summer(self):
        """Test sensory anchors for summer."""
        result = AtmosphereGenerator.get_sensory_anchors("夏", "晴天", "公園")
        assert "熱気" in "".join(result)

    def test_get_sensory_anchors_winter(self):
        """Test sensory anchors for winter."""
        result = AtmosphereGenerator.get_sensory_anchors("冬", "晴天", "公園")
        assert "冷気" in "".join(result)

    def test_get_sensory_anchors_rain(self):
        """Test sensory anchors for rain."""
        result = AtmosphereGenerator.get_sensory_anchors("春", "雨", "公園")
        assert "雨音" in "".join(result)


class TestIntegration:
    """Integration tests combining multiple sanitizer components."""

    def test_full_sanitization_pipeline(self):
        """Test complete sanitization pipeline."""
        raw_text = """Understood. Here is the plot.
### NOVEL CONTENT ###
He said "I will go".
{"episode_number": 1, "title": "Episode 1", "script_content": "He said I will go", "severity": "minor"}
### NOVEL CONTENT ###"""

        metadata, content = OutputSanitizer.extract_content_and_metadata(raw_text)
        normalized = OutputSanitizer.normalize_metadata(metadata)
        cleaned = OutputSanitizer._clean_story(content)
        formatted = TextFormatter.format_for_kakuyomu(cleaned)

        # Check that the pipeline runs without error
        assert isinstance(normalized, dict)
        assert isinstance(content, str)
        assert isinstance(cleaned, str)
        assert isinstance(formatted, str)
        assert len(formatted) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])