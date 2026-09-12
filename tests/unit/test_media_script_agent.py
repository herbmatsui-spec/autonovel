from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agents.media_script_agent import (
    MediaScriptAgent,
    MangaScriptOutput,
    PanelScript,
    AudioDramaScriptOutput,
    AudioDramaLine,
)


class MockLLMProvider:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    def generate(self, prompt: str, temperature: float = 0.4) -> str:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


def test_manga_script_output_schema():
    panel = PanelScript(
        panel_number=1,
        camera_angle="close_up",
        visual_description="主人公が驚いた表情",
        dialogues=[{"speaker": "主人公", "text": "なんだって？"}],
        sfx=["SE: 衝撃音"],
        narration="突然の出来事に呆然とする"
    )
    output = MangaScriptOutput(
        page_number=1,
        panels=[panel],
        scene_mood="surprise"
    )
    assert output.page_number == 1
    assert len(output.panels) == 1
    assert output.panels[0].camera_angle == "close_up"


def test_audio_drama_script_output_schema():
    line = AudioDramaLine(
        character="主人公",
        text="行くぞ！",
        emotion="shout",
        direction="[激昂・大声・早口]",
        audio_cues_before=[{"type": "sfx", "name": "tension", "description": "緊張感", "duration": 1.0}],
        audio_cues_after=[{"type": "sfx", "name": "impact", "description": "インパクト", "duration": 0.5}]
    )
    output = AudioDramaScriptOutput(
        episode_title="第1話",
        lines=[line],
        bgm_plan=[{"scene": "battle", "track": "battle_theme", "mood": "intense"}],
        sfx_plan=[{"trigger": "shout", "sound": "impact", "timing": "on_line"}],
        cast_requirements={"characters": ["主人公"], "required_emotions": ["shout"], "narrator_needed": False, "total_voice_actors": 1}
    )
    assert output.episode_title == "第1話"
    assert len(output.lines) == 1
    assert output.lines[0].emotion == "shout"


def test_clean_json_markdown():
    agent = MediaScriptAgent(llm_provider=None)
    
    raw_with_markdown = '```json\n{"key": "value"}\n```'
    result = agent._clean_json_markdown(raw_with_markdown)
    assert result == {"key": "value"}
    
    raw_without_markdown = '{"key": "value"}'
    result = agent._clean_json_markdown(raw_without_markdown)
    assert result == {"key": "value"}
    
    raw_with_extra = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
    result = agent._clean_json_markdown(raw_with_extra)
    assert result == {"key": "value"}


def test_split_into_scenes():
    agent = MediaScriptAgent(llm_provider=None)
    
    short_text = "短いテキストです。"
    scenes = agent._split_into_scenes(short_text, max_chars=1500)
    assert len(scenes) == 1
    assert scenes[0] == short_text
    
    long_text = "シーン1の内容。\n\nシーン2の内容。\n\nシーン3の内容。" * 100
    scenes = agent._split_into_scenes(long_text, max_chars=500)
    assert len(scenes) > 1


def test_build_character_context():
    agent = MediaScriptAgent(llm_provider=None)
    characters = [
        {"name": "Protagonist", "personality": "Brave", "first_person": "I", "speech_pattern": "Male"},
        {"name": "Heroine", "personality": "Kind", "first_person": "I", "speech_pattern": "Polite"}
    ]
    context = agent._build_character_context(characters)
    assert "Protagonist" in context
    assert "Brave" in context
    assert "Heroine" in context
    assert "Kind" in context


def test_fallback_manga_script():
    agent = MediaScriptAgent(llm_provider=None)
    chapter_text = "Test chapter content.\n\nProtagonist faced difficulties.\n\"Let's go\" he said."
    characters = [{"name": "Protagonist", "personality": "Brave"}]
    results = agent._fallback_manga_script(chapter_text, characters)
    assert len(results) > 0
    assert all(isinstance(r, MangaScriptOutput) for r in results)
    assert all(len(r.panels) > 0 for r in results)


def test_fallback_audio_script():
    agent = MediaScriptAgent(llm_provider=None)
    chapter_text = "Test chapter content.\n\nProtagonist faced difficulties.\n\"Let's go\" he said."
    characters = [{"name": "Protagonist", "personality": "Brave"}]
    result = agent._fallback_audio_script(chapter_text, characters)
    assert isinstance(result, AudioDramaScriptOutput)
    assert len(result.lines) > 0


def test_generate_manga_script_with_mock_llm():
    mock_response = json.dumps({
        "page_number": 1,
        "panels": [
            {
                "panel_number": 1,
                "camera_angle": "medium",
                "visual_description": "Test scene",
                "dialogues": [{"speaker": "Protagonist", "text": "Test"}],
                "sfx": [],
                "narration": "Test narration"
            }
        ],
        "scene_mood": "neutral"
    })
    agent = MediaScriptAgent(llm_provider=None)
    
    with patch.object(agent, '_call_llm', return_value=mock_response) as mock_call:
        chapter_text = "Test chapter content."
        characters = [{"name": "Protagonist", "personality": "Brave"}]
        results = agent.generate_manga_script(chapter_text, characters)
        
        mock_call.assert_called_once()
        assert len(results) == 1
        assert results[0].page_number == 1
        assert len(results[0].panels) == 1
        assert results[0].panels[0].camera_angle == "medium"


def test_generate_audio_script_with_mock_llm():
    mock_response = json.dumps({
        "episode_title": "Test Episode",
        "lines": [
            {
                "character": "Protagonist",
                "text": "Test dialogue",
                "emotion": "joy",
                "direction": "[Bright and cheerful]",
                "audio_cues_before": [],
                "audio_cues_after": []
            }
        ],
        "bgm_plan": [{"scene": "daily", "track": "peaceful", "mood": "calm"}],
        "sfx_plan": [],
        "cast_requirements": {"characters": ["Protagonist"], "required_emotions": ["joy"], "narrator_needed": False, "total_voice_actors": 1}
    })
    agent = MediaScriptAgent(llm_provider=None)
    
    with patch.object(agent, '_call_llm', return_value=mock_response) as mock_call:
        chapter_text = "Test chapter content."
        characters = [{"name": "Protagonist", "personality": "Brave"}]
        result = agent.generate_audio_script(chapter_text, characters)
        
        mock_call.assert_called_once()
        assert result.episode_title == "Test Episode"
        assert len(result.lines) == 1
        assert result.lines[0].emotion == "joy"


def test_generate_manga_script_fallback_on_llm_error():
    mock_llm = MockLLMProvider(["invalid json"])
    agent = MediaScriptAgent(llm_provider=mock_llm)
    
    chapter_text = "Test chapter content. " * 100
    characters = [{"name": "Protagonist", "personality": "Brave"}]
    results = agent.generate_manga_script(chapter_text, characters)
    
    assert len(results) > 0
    assert all(isinstance(r, MangaScriptOutput) for r in results)


def test_generate_audio_script_fallback_on_llm_error():
    mock_llm = MockLLMProvider(["invalid json"])
    agent = MediaScriptAgent(llm_provider=mock_llm)
    
    chapter_text = "Test chapter content."
    characters = [{"name": "Protagonist", "personality": "Brave"}]
    result = agent.generate_audio_script(chapter_text, characters)
    
    assert isinstance(result, AudioDramaScriptOutput)
    assert len(result.lines) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])