import os
import tempfile
import pytest
from src.services.audio.audio_combiner import AudioCombiner
from src.services.audio.audio_storage import AudioStorageService
from src.services.audio.chapter_synthesizer import ChapterAudioSynthesizer
from src.services.audio.mock_client import MockAudioSynthesisClient


def test_audio_combiner_with_mock_clips():
    client = MockAudioSynthesisClient(sample_rate=24000, default_duration=0.2)
    # 2つのモックWAVを取得
    import asyncio
    clip1 = asyncio.run(client.synthesize(None)).audio_bytes
    clip2 = asyncio.run(client.synthesize(None)).audio_bytes

    combined = AudioCombiner.combine_wav_clips([clip1, clip2], silence_duration_sec=0.2)
    assert combined.startswith(b"RIFF")
    assert len(combined) > len(clip1)


def test_audio_storage_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AudioStorageService(base_dir=tmpdir)
        dummy_wav = b"RIFF....WAVEfmt ...."
        path = storage.save_chapter_audio(book_id=1, episode_num=1, audio_bytes=dummy_wav)
        assert os.path.exists(path)
        assert path.endswith("ep_1_full.wav")


@pytest.mark.asyncio
async def test_chapter_audio_synthesizer():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = MockAudioSynthesisClient()
        storage = AudioStorageService(base_dir=tmpdir)
        synth = ChapterAudioSynthesizer(audio_client=client, storage_service=storage)

        text = """
        「こんにちは」とアリスは言った。
        街は賑わっていた。
        """
        res = await synth.synthesize_chapter(
            book_id=10,
            episode_num=2,
            chapter_text=text,
            characters=["アリス"],
        )
        assert res["file_path"] != ""
        assert os.path.exists(res["file_path"])
        assert res["lines_count"] >= 2
        assert res["duration_seconds"] > 0
