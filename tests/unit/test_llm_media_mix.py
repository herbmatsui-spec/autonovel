from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from src.easy_mode.phase3.media_mix import (
    MediaFormat,
    MediaScript,
    Panel,
    VoiceLine,
    AudioCue,
    MangaScriptGenerator,
    AudioDramaScriptGenerator,
    MediaMixExporter,
    create_media_mix_exporter,
)
from src.easy_mode import EpisodeResult, SeriesResult


class MockMediaScriptAgent:
    """Mock MediaScriptAgent for testing"""
    
    def __init__(self, manga_response=None, audio_response=None):
        self.manga_response = manga_response or self._default_manga_response()
        self.audio_response = audio_response or self._default_audio_response()
        self.manga_call_count = 0
        self.audio_call_count = 0
    
    def _default_manga_response(self):
        return [
            MagicMock(
                page_number=1,
                panels=[
                    MagicMock(
                        panel_number=1,
                        visual_description="Test scene description",
                        dialogues=[{"speaker": "Protagonist", "text": "Test dialogue"}],
                        sfx=["SE: Test sound"],
                        narration="Test narration",
                        camera_angle="close_up",
                    ),
                    MagicMock(
                        panel_number=2,
                        visual_description="Test scene 2",
                        dialogues=[{"speaker": "Heroine", "text": "Response"}],
                        sfx=[],
                        narration="",
                        camera_angle="medium",
                    ),
                ],
                scene_mood="tense",
            )
        ]
    
    def _default_audio_response(self):
        return MagicMock(
            episode_title="Test Episode",
            lines=[
                MagicMock(
                    character="Protagonist",
                    text="Test dialogue",
                    emotion="anger",
                    direction="[激昂・大声・早口]",
                    audio_cues_before=[
                        {"type": "sfx", "name": "tension", "description": "緊張感", "duration": 1.0, "volume": 1.0, "fade_in": 0.0, "fade_out": 0.0}
                    ],
                    audio_cues_after=[
                        {"type": "sfx", "name": "impact", "description": "インパクト", "duration": 0.5, "volume": 1.0, "fade_in": 0.0, "fade_out": 0.0}
                    ],
                ),
                MagicMock(
                    character="Heroine",
                    text="Response",
                    emotion="sadness",
                    direction="[静か・低め・間を置く]",
                    audio_cues_before=[],
                    audio_cues_after=[],
                ),
            ],
            bgm_plan=[{"scene": "battle", "track": "battle_theme", "mood": "intense"}],
            sfx_plan=[{"trigger": "dialogue", "sound": "impact", "timing": "on_line"}],
            cast_requirements={
                "characters": ["Protagonist", "Heroine"],
                "required_emotions": ["anger", "sadness"],
                "narrator_needed": False,
                "total_voice_actors": 2,
            },
        )
    
    def generate_manga_script(self, chapter_text: str, characters: list[dict]):
        self.manga_call_count += 1
        return self.manga_response
    
    def generate_audio_script(self, chapter_text: str, characters: list[dict]):
        self.audio_call_count += 1
        return self.audio_response


def make_test_episode(num: int = 1) -> EpisodeResult:
    content = (
        f"第{num}話のテスト本文です。\n\n"
        "主人公は敵と対峙した。\n"
        "「覚悟しろ」と主人公は言った。\n\n"
        "ヒロインは震える声で答えた。\n"
        "「怖い…でも逃げない」"
    )
    return EpisodeResult(
        episode_num=num,
        title=f"第{num}話",
        content=content,
        word_count=len(content),
        audit_score=80.0,
        audit_passed=True,
        rewrite_count=0,
        spice_elements=[],
        metadata={},
        needs_human_review=False,
    )


def make_test_series(genre: str = "Test Genre", episode_count: int = 1) -> SeriesResult:
    eps = [make_test_episode(i + 1) for i in range(episode_count)]
    return SeriesResult(
        genre=genre,
        title="Test Series",
        concept="Test concept",
        total_episodes=episode_count,
        episodes=eps,
        bible={},
        plot_outline=[],
        metadata={"prologue": "Test prologue"},
    )


def make_test_preset() -> dict:
    return {
        "genre": "Test Genre",
        "style": {"manga_notes": "Test style"},
        "characters": {
            "archetypes": {
                "protagonist": {
                    "name_pattern": "主人公",
                    "personality": "勇敢",
                    "speech_patterns": {
                        "first_person": "俺",
                        "tone": "男性的",
                    },
                },
                "heroine": {
                    "name_pattern": "ヒロイン",
                    "personality": "優しい",
                    "speech_patterns": {
                        "first_person": "私",
                        "tone": "丁寧",
                    },
                },
            }
        },
        "erotic": {},
    }


def test_manga_generator_with_llm_agent():
    """Test MangaScriptGenerator uses LLM agent when provided"""
    mock_agent = MockMediaScriptAgent()
    generator = MangaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    assert script.format == MediaFormat.MANGA
    assert script.metadata.get("generated_by") == "llm"
    assert mock_agent.manga_call_count == 1
    assert len(script.panels) == 2
    assert script.panels[0].camera_angle == "close_up"
    assert "Protagonist：「Test dialogue」" in script.panels[0].dialogue


def test_audio_generator_with_llm_agent():
    """Test AudioDramaScriptGenerator uses LLM agent when provided"""
    mock_agent = MockMediaScriptAgent()
    generator = AudioDramaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    assert script.format == MediaFormat.AUDIO_DRAMA
    assert script.metadata.get("generated_by") == "llm"
    assert mock_agent.audio_call_count == 1
    assert len(script.voice_lines) == 2
    assert script.voice_lines[0].emotion == "anger"
    assert script.voice_lines[0].direction == "[激昂・大声・早口]"
    assert len(script.voice_lines[0].audio_cues_before) == 1
    assert script.voice_lines[0].audio_cues_before[0].name == "tension"


def test_manga_generator_fallback_when_llm_fails():
    """Test MangaScriptGenerator falls back to rule-based when LLM fails"""
    mock_agent = MockMediaScriptAgent()
    mock_agent.generate_manga_script = MagicMock(side_effect=Exception("LLM Error"))
    
    generator = MangaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    assert script.metadata.get("generated_by") == "rule_based"
    assert len(script.panels) > 0


def test_audio_generator_fallback_when_llm_fails():
    """Test AudioDramaScriptGenerator falls back to rule-based when LLM fails"""
    mock_agent = MockMediaScriptAgent()
    mock_agent.generate_audio_script = MagicMock(side_effect=Exception("LLM Error"))
    
    generator = AudioDramaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    assert script.metadata.get("generated_by") == "rule_based"
    assert len(script.voice_lines) > 0


def test_create_media_mix_exporter_with_script_agent():
    """Test factory function passes script_agent to generators"""
    mock_agent = MockMediaScriptAgent()
    exporter = create_media_mix_exporter(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    assert exporter.script_agent is mock_agent
    assert exporter.manga_gen.script_agent is mock_agent
    assert exporter.audio_gen.script_agent is mock_agent


def test_media_mix_exporter_export_all():
    """Test MediaMixExporter exports all formats"""
    mock_agent = MockMediaScriptAgent()
    exporter = MediaMixExporter(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    scripts = exporter.export_all(episode, series, [
        MediaFormat.MANGA,
        MediaFormat.AUDIO_DRAMA,
    ])
    
    assert MediaFormat.MANGA in scripts
    assert MediaFormat.AUDIO_DRAMA in scripts
    assert scripts[MediaFormat.MANGA].metadata.get("generated_by") == "llm"
    assert scripts[MediaFormat.AUDIO_DRAMA].metadata.get("generated_by") == "llm"


def test_manga_character_context_injection():
    """Test character context is properly built and passed to LLM"""
    mock_agent = MockMediaScriptAgent()
    generator = MangaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    # Capture the characters passed to the agent
    captured_chars = []
    original_generate = mock_agent.generate_manga_script
    def capture_chars(text, chars):
        captured_chars.append(chars)
        return original_generate(text, chars)
    mock_agent.generate_manga_script = capture_chars
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    generator.generate(episode, series)
    
    assert len(captured_chars) == 1
    chars = captured_chars[0]
    assert len(chars) == 2
    assert any(c["name"] == "主人公" for c in chars)
    assert any(c["name"] == "ヒロイン" for c in chars)


def test_audio_character_context_injection():
    """Test character context is properly built and passed to LLM for audio"""
    mock_agent = MockMediaScriptAgent()
    generator = AudioDramaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    captured_chars = []
    original_generate = mock_agent.generate_audio_script
    def capture_chars(text, chars):
        captured_chars.append(chars)
        return original_generate(text, chars)
    mock_agent.generate_audio_script = capture_chars
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    generator.generate(episode, series)
    
    assert len(captured_chars) == 1
    chars = captured_chars[0]
    assert len(chars) == 2


def test_direction_quality_in_generated_audio():
    """Test that generated audio includes quality direction markers"""
    mock_agent = MockMediaScriptAgent()
    generator = AudioDramaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    # Check that direction contains emotional markers
    for line in script.voice_lines:
        if line.emotion != "neutral":
            assert "[" in line.direction and "]" in line.direction
            assert len(line.direction) > 2


def test_manga_panels_have_camera_angles():
    """Test that generated manga panels have proper camera angles"""
    mock_agent = MockMediaScriptAgent()
    generator = MangaScriptGenerator(
        genre="Test Genre",
        preset=make_test_preset(),
        script_agent=mock_agent,
    )
    
    episode = make_test_episode(1)
    series = make_test_series()
    
    script = generator.generate(episode, series)
    
    for panel in script.panels:
        assert panel.camera_angle in ["close_up", "medium", "wide", "bird_eye", "low_angle", "over_shoulder", "dynamic"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])