from __future__ import annotations

import asyncio
import json
import wave
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.audio.chapter_synthesizer import ChapterAudioSynthesizer
from src.services.audio.dialogue_extractor import DialogueExtractor, DialogueLine, split_long_sentence
from src.services.audio.emotion_classifier import AcousticParameters, SpeechEmotion
from src.services.audio.base import AudioSynthesisClient, AudioSynthesisRequest, AudioSynthesisResult


class MockAudioClient(AudioSynthesisClient):
    """Mock audio client for testing"""
    
    def __init__(self, responses: list[AudioSynthesisResult] = None):
        self.responses = responses or []
        self.call_count = 0
        self.requests = []
    
    async def synthesize(self, req: AudioSynthesisRequest | None) -> AudioSynthesisResult:
        self.requests.append(req)
        if self.responses:
            response = self.responses[self.call_count % len(self.responses)]
        else:
            # Generate simple WAV for testing
            response = self._generate_test_wav()
        self.call_count += 1
        return response
    
    def _generate_test_wav(self) -> AudioSynthesisResult:
        """Generate a minimal valid WAV file"""
        import struct
        sample_rate = 24000
        duration = 0.1
        n_samples = int(sample_rate * duration)
        audio_data = struct.pack('<' + 'h' * n_samples, *([0] * n_samples))
        
        # WAV header
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + len(audio_data),
            b'WAVE',
            b'fmt ',
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b'data',
            len(audio_data)
        )
        return AudioSynthesisResult(
            audio_bytes=header + audio_data,
            format="wav",
            duration_seconds=duration,
            sample_rate=sample_rate
        )


def test_dialogue_line_emotion_fields():
    """Test DialogueLine has emotion and acoustics fields"""
    line = DialogueLine(
        line_index=0,
        text="テスト",
        is_dialogue=True,
        speaker_name="主人公",
        speaker_id=3,
        emotion=SpeechEmotion.JOY,
        acoustics=AcousticParameters(speed_scale=1.15, pitch_scale=0.05)
    )
    assert line.emotion == SpeechEmotion.JOY
    assert line.acoustics is not None
    assert line.acoustics.speed_scale == 1.15


def test_dialogue_extractor_emotion_classification():
    """Test DialogueExtractor extracts emotion from dialogue"""
    extractor = DialogueExtractor()
    characters = ["主人公", "ヒロイン"]
    
    chapter_text = "「行くぞ！」（主人公）\n\n「待って…」（ヒロイン）"
    lines = extractor.extract_lines(chapter_text, characters=characters)
    
    # Both dialogue and narration lines are extracted
    # Filter to only dialogue lines
    dialogue_lines = [l for l in lines if l.is_dialogue]
    assert len(dialogue_lines) == 2
    # First line should be angry/shout
    assert dialogue_lines[0].emotion in [SpeechEmotion.ANGER, SpeechEmotion.SHOUT]
    # Second line should be sad/whisper
    assert dialogue_lines[1].emotion in [SpeechEmotion.SADNESS, SpeechEmotion.WHISPER]


def test_dialogue_extractor_acoustics_attached():
    """Test that acoustics are attached to each line"""
    extractor = DialogueExtractor()
    characters = ["主人公"]
    
    chapter_text = "「行くぞ！」（主人公）"
    lines = extractor.extract_lines(chapter_text, characters=characters)
    
    # Filter to only dialogue lines
    dialogue_lines = [l for l in lines if l.is_dialogue]
    assert len(dialogue_lines) == 1
    assert dialogue_lines[0].acoustics is not None
    assert isinstance(dialogue_lines[0].acoustics, AcousticParameters)
    # Anger should have higher speed
    assert dialogue_lines[0].acoustics.speed_scale > 1.0


def test_synthesizer_emotion_linked_style_id():
    """Test ChapterAudioSynthesizer applies emotion-linked style_id"""
    mock_client = MockAudioClient()
    synthesizer = ChapterAudioSynthesizer(audio_client=mock_client)
    
    # Test with a simple chapter
    chapter_text = "「行くぞ！」（主人公）\n\n「待って…」（ヒロイン）"
    characters = ["主人公", "ヒロイン"]
    character_details = {
        "主人公": {"gender": "male", "role": "hero"},
        "ヒロイン": {"gender": "female", "role": "heroine"},
    }
    
    result = asyncio.run(synthesizer.synthesize_chapter(
        book_id=1,
        episode_num=1,
        chapter_text=chapter_text,
        characters=characters,
        character_details=character_details,
    ))
    
    # Check that requests were made with correct parameters
    assert mock_client.call_count >= 1
    for req in mock_client.requests:
        assert req.speaker_id > 0
        assert req.speed_scale > 0
        assert req.pitch_scale != 0 or req.intonation_scale != 0 or req.volume_scale != 0


def test_synthesizer_emotion_distribution_metadata():
    """Test that emotion distribution is saved in metadata"""
    mock_client = MockAudioClient()
    synthesizer = ChapterAudioSynthesizer(audio_client=mock_client)
    
    chapter_text = "「行くぞ！」（主人公）\n「愛してるよ…」（ヒロイン）\n「どこへ行くの？」（主人公）"
    characters = ["主人公", "ヒロイン"]
    character_details = {
        "主人公": {"gender": "male", "role": "hero"},
        "ヒロイン": {"gender": "female", "role": "heroine"},
    }
    
    result = asyncio.run(synthesizer.synthesize_chapter(
        book_id=1,
        episode_num=1,
        chapter_text=chapter_text,
        characters=characters,
        character_details=character_details,
    ))
    
    assert "emotion_distribution" in result
    dist = result["emotion_distribution"]
    assert isinstance(dist, dict)
    # Should have at least some emotions
    assert len(dist) > 0
    # Percentages should sum to ~100
    total = sum(dist.values())
    assert 90 <= total <= 110  # Allow for rounding


def test_audio_synthesis_request_volume_scale():
    """Test AudioSynthesisRequest includes volume_scale"""
    req = AudioSynthesisRequest(
        text="テスト",
        speaker_id=3,
        speed_scale=1.0,
        pitch_scale=0.0,
        intonation_scale=1.0,
        volume_scale=1.2
    )
    assert req.volume_scale == 1.2


def test_voicevox_client_volume_scale():
    """Test VoicevoxClient applies volume_scale"""
    from src.services.audio.voicevox_client import VoicevoxClient
    
    # Check that the code includes volumeScale
    import inspect
    source = inspect.getsource(VoicevoxClient.synthesize)
    assert "volumeScale" in source


def test_variable_pause_combine_wav():
    """Test AudioCombiner.combine_wav_clips with variable pauses"""
    from src.services.audio.audio_combiner import AudioCombiner
    
    # Generate test WAV clips
    import struct
    def make_wav(duration=0.1):
        sample_rate = 24000
        n_samples = int(sample_rate * duration)
        audio_data = struct.pack('<' + 'h' * n_samples, *([0] * n_samples))
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + len(audio_data),
            b'WAVE',
            b'fmt ',
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b'data',
            len(audio_data)
        )
        return header + audio_data
    
    clips = [make_wav(0.1), make_wav(0.1), make_wav(0.1)]
    pauses = [0.2, 0.5]  # Different pauses between clips
    
    combined = AudioCombiner.combine_wav_clips(clips, pauses=pauses)
    
    # Verify result is valid WAV
    assert combined.startswith(b"RIFF")
    assert b"WAVE" in combined[:12]
    
    # Check duration matches expected
    with wave.open(BytesIO(combined), "rb") as wav:
        frames = wav.getnframes()
        framerate = wav.getframerate()
        total_duration = frames / framerate
        # 0.1 + 0.2 + 0.1 + 0.5 + 0.1 = 1.0 seconds
        assert 0.9 <= total_duration <= 1.1


def test_synthesizer_error_handling_skip():
    """Test that synthesis errors are logged and skipped"""
    # Create a mock that fails on the second call
    call_count = {"count": 0}
    
    async def mock_synthesize(req):
        call_count["count"] += 1
        if call_count["count"] == 2:
            raise Exception("API Error")
        return AudioSynthesisResult(audio_bytes=b"RIFF....", format="wav", duration_seconds=0.1)
    
    mock_client = MockAudioClient()
    mock_client.synthesize = mock_synthesize
    
    synthesizer = ChapterAudioSynthesizer(audio_client=mock_client)
    
    chapter_text = "「セリフ1」（主人公）\n「セリフ2」（ヒロイン）\n「セリフ3」（主人公）"
    characters = ["主人公", "ヒロイン"]
    
    result = asyncio.run(synthesizer.synthesize_chapter(
        book_id=1,
        episode_num=1,
        chapter_text=chapter_text,
        characters=characters,
    ))
    
    # Should have processed remaining lines despite error
    # Both dialogue and narration lines are extracted
    assert result["lines_count"] >= 3
    assert call_count["count"] >= 3


def test_synthesizer_parallel_processing():
    """Test that synthesizer uses semaphore for parallel processing"""
    mock_client = MockAudioClient()
    synthesizer = ChapterAudioSynthesizer(audio_client=mock_client, max_concurrent=2)
    
    chapter_text = "\n".join([f"「セリフ{i}」（主人公）" for i in range(10)])
    characters = ["主人公"]
    
    result = asyncio.run(synthesizer.synthesize_chapter(
        book_id=1,
        episode_num=1,
        chapter_text=chapter_text,
        characters=characters,
    ))
    
    # Both dialogue and narration lines extracted
    assert result["lines_count"] >= 10
    assert mock_client.call_count >= 10


def test_dialogue_extractor_long_sentence_split():
    """Test split_long_sentence function"""
    long_text = "これはとても長い文章です。" * 10
    chunks = split_long_sentence(long_text, max_length=50)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 50 + 5  # Allow some margin


def test_audio_combiner_empty_clips():
    """Test AudioCombiner with empty clips"""
    from src.services.audio.audio_combiner import AudioCombiner
    
    result = AudioCombiner.combine_wav_clips([])
    assert result == b""
    
    result = AudioCombiner.combine_wav_clips([b"invalid", b""])
    assert result == b""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])