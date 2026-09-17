"""音声合成アダプタ（OpenAI TTS, ElevenLabs, Mock, Factory）の単体テスト (v5.0 Step 7〜10)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.audio.adapters.base import (
    AudioTtsAdapter,
    TtsRequest,
    TtsResult,
)
from src.services.audio.adapters.elevenlabs_adapter import (
    ElevenLabsAdapter,
    OpenAIttsAdapter,
)
from src.services.audio.factory import (
    MockTtsAdapter,
    get_tts_adapter,
)


class TestTtsRequest:
    def test_request_defaults(self):
        req = TtsRequest(text="吾輩は猫である。")
        assert req.text == "吾輩は猫である。"
        assert req.voice_id == "default"
        assert req.speed == 1.0
        assert req.format == "mp3"


class TestMockTtsAdapter:
    def test_provider_name(self):
        adapter = MockTtsAdapter()
        assert adapter.provider_name == "mock"

    @pytest.mark.asyncio
    async def test_synthesize_mock(self):
        adapter = MockTtsAdapter()
        req = TtsRequest(text="テスト音声テキスト")
        res = await adapter.synthesize(req)

        assert res.provider == "mock"
        assert res.cost_usd == 0.0
        assert res.character_count == len("テスト音声テキスト")
        assert len(res.audio_bytes) > 0


class TestOpenAIttsAdapter:
    def test_provider_name(self):
        adapter = OpenAIttsAdapter(api_key="sk-test-openai")
        assert adapter.provider_name == "openai_tts"

    @pytest.mark.asyncio
    async def test_synthesize_openai(self):
        dummy_audio = b"ID3dummy-openai-mp3-bytes"

        mock_resp = MagicMock()
        mock_resp.content = dummy_audio
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        adapter = OpenAIttsAdapter(api_key="sk-test", client=mock_client)
        req = TtsRequest(text="あいうえおかきくけこ", voice_id="alloy", speed=1.2, format="mp3")
        res = await adapter.synthesize(req)

        assert res.provider == "openai_tts"
        assert res.audio_bytes == dummy_audio
        assert res.character_count == 10
        # 10文字 / 1000 * 0.015 = 0.00015
        assert pytest.approx(res.cost_usd, 0.00001) == 0.00015

        # 検証: POST ペイロード
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "tts-1"
        assert payload["voice"] == "alloy"
        assert payload["speed"] == 1.2


class TestElevenLabsAdapter:
    def test_provider_name(self):
        adapter = ElevenLabsAdapter(api_key="xi-test-key")
        assert adapter.provider_name == "elevenlabs"

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs(self):
        dummy_audio = b"dummy-elevenlabs-bytes"

        mock_resp = MagicMock()
        mock_resp.content = dummy_audio
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        adapter = ElevenLabsAdapter(api_key="xi-test", client=mock_client)
        req = TtsRequest(text="こんにちは世界")
        res = await adapter.synthesize(req)

        assert res.provider == "elevenlabs"
        assert res.audio_bytes == dummy_audio
        assert res.character_count == 7
        assert pytest.approx(res.cost_usd, 0.00001) == (7 / 1000.0) * 0.030


class TestTtsFactory:
    def test_factory_returns_mock_default(self, monkeypatch):
        monkeypatch.delenv("TTS_PROVIDER", raising=False)
        adapter = get_tts_adapter()
        assert adapter.provider_name == "mock"

    def test_factory_returns_mock_on_unknown(self):
        adapter = get_tts_adapter("unknown_tts_provider")
        assert adapter.provider_name == "mock"

    def test_factory_returns_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-tts-test")
        adapter = get_tts_adapter("openai")
        assert adapter.provider_name == "openai_tts"
        assert adapter.api_key == "sk-tts-test"

    def test_factory_returns_elevenlabs(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "xi-tts-test")
        adapter = get_tts_adapter("elevenlabs")
        assert adapter.provider_name == "elevenlabs"
        assert adapter.api_key == "xi-tts-test"
