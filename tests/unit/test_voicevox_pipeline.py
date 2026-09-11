import asyncio
import pytest
from src.services.audio.base import AudioSynthesisRequest
from src.services.audio.dialogue_extractor import DialogueExtractor, split_long_sentence
from src.services.audio.factory import get_audio_client
from src.services.audio.mock_client import MockAudioSynthesisClient
from src.services.audio.speaker_mapper import assign_speaker_id


def test_sentence_splitting():
    text = "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。"
    parts = split_long_sentence(text, max_length=20)
    assert len(parts) >= 2
    for p in parts:
        assert len(p) <= 25


def test_dialogue_extraction_and_speaker_resolution():
    extractor = DialogueExtractor()
    sample = """
    「おはよう、アイリス」とルクスは挨拶した。
    アイリスは微笑みながら答えた。
    「ええ、いい朝ね」
    今日も平和な一日が始まる。
    """
    lines = extractor.extract_lines(sample, characters=["アイリス", "ルクス"])
    assert len(lines) >= 4

    dialogues = [l for l in lines if l.is_dialogue]
    assert len(dialogues) == 2
    assert dialogues[0].text == "おはよう、アイリス"
    assert dialogues[0].speaker_name == "ルクス"
    assert dialogues[1].text == "ええ、いい朝ね"
    assert dialogues[1].speaker_name == "アイリス"

    narrations = [l for l in lines if not l.is_dialogue]
    assert any("今日も平和な一日が始まる" in n.text for n in narrations)


def test_speaker_mapper():
    assert assign_speaker_id("narration") == 3
    assert assign_speaker_id("ルクス", gender="male") == 13
    assert assign_speaker_id("アイリス", gender="female", role="heroine") == 2
    assert assign_speaker_id("妹キャラ", gender="female", role="sweet") == 1


@pytest.mark.asyncio
async def test_mock_audio_client():
    client = MockAudioSynthesisClient(sample_rate=24000)
    req = AudioSynthesisRequest(text="テスト音声です。", speaker_id=3)
    res = await client.synthesize(req)
    assert res.audio_bytes.startswith(b"RIFF")
    assert res.format == "wav"
    assert res.duration_seconds > 0


def test_audio_factory():
    client = get_audio_client("mock")
    assert isinstance(client, MockAudioSynthesisClient)
