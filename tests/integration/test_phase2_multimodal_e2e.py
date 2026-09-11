import asyncio
import os
import tempfile
import pytest
from src.services.illustration.mock_client import MockImageClient
from src.services.illustration.base import ImageGenerationRequest
from src.services.audio.chapter_synthesizer import ChapterAudioSynthesizer
from src.services.audio.mock_client import MockAudioSynthesisClient
from src.services.audio.audio_storage import AudioStorageService
from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder


@pytest.mark.asyncio
async def test_phase2_multimodal_full_pipeline():
    # 1. 挿絵画像生成 (Mock)
    img_client = MockImageClient()
    img_res = await img_client.generate_image(ImageGenerationRequest(prompt="ファンタジー勇者"))
    assert img_res.image_bytes.startswith(b"\x89PNG")

    # 2. VOICEVOX 音声合成 (Mock)
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_client = MockAudioSynthesisClient()
        audio_storage = AudioStorageService(base_dir=tmpdir)
        synth = ChapterAudioSynthesizer(audio_client=audio_client, storage_service=audio_storage)

        text = "「行くぞ」と｜勇者《ゆうしゃ》は叫んだ。\n大地が揺れた。"
        audio_res = await synth.synthesize_chapter(
            book_id=99,
            episode_num=1,
            chapter_text=text,
            characters=["勇者"],
        )
        assert os.path.exists(audio_res["file_path"])
        assert audio_res["duration_seconds"] > 0

    # 3. 商用縦書きEPUB 3生成
    builder = CommercialEpubBuilder()
    epub_bytes = builder.build_commercial_epub(
        {"title": "マルチモーダル大戦", "author": "AI"},
        [{"title": "第1話", "content": text}],
    )
    assert len(epub_bytes) > 500
    assert epub_bytes.startswith(b"PK")
