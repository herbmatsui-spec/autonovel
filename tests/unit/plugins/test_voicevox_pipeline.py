"""Step 20 検証テスト: VOICEVOX 音声合成プラグイン（Graceful Fallback）."""

from __future__ import annotations

import io
import struct
import wave
from pathlib import Path
from unittest.mock import patch

from src.plugins.audio.plugin import AudioPlugin
from src.plugins.audio.voicevox import VoicevoxProvider, VoicevoxUnavailableError


def _make_wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(struct.pack("<h", 0) * 100)
    return buf.getvalue()


class TestVoicevoxAvailability:
    def test_unavailable_when_server_down(self):
        provider = VoicevoxProvider(base_url="http://localhost:59999")
        assert provider.is_available() is False

    def test_available_with_mocked_server(self):
        provider = VoicevoxProvider(base_url="http://localhost:59999")
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"0.14"
            assert provider.is_available() is True


class TestVoicevoxFallback:
    def test_fallback_skip_returns_none(self, tmp_path):
        """サーバー不在時 fallback_mode=skip は None を返すこと。"""
        provider = VoicevoxProvider(base_url="http://localhost:59999", fallback_mode="skip")
        result = provider.synthesize("テスト", tmp_path / "out.wav")
        assert result is None
        assert not (tmp_path / "out.wav").exists()

    def test_fallback_empty_file_generates_silent_wav(self, tmp_path):
        """サーバー不在時 fallback_mode=empty_file は無音 WAV を生成すること。"""
        provider = VoicevoxProvider(
            base_url="http://localhost:59999", fallback_mode="empty_file"
        )
        out = tmp_path / "out.wav"
        result = provider.synthesize("テスト", out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_synthesis_failure_falls_back(self, tmp_path):
        """合成中にエラーが発生してもフォールバックすること。"""
        provider = VoicevoxProvider(base_url="http://localhost:59999", fallback_mode="skip")
        with (
            patch.object(provider, "is_available", return_value=True),
            patch("urllib.request.urlopen", side_effect=OSError("boom")),
        ):
            result = provider.synthesize("テスト", tmp_path / "out.wav")
        assert result is None

    def test_synthesis_success_writes_wav(self, tmp_path):
        """サーバー応答が正常なら WAV を書き出すこと。"""
        provider = VoicevoxProvider(base_url="http://localhost:59999")
        wav_bytes = _make_wav_bytes()

        def fake_urlopen(req, timeout=0):  # noqa: ANN001, ARG001
            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return wav_bytes if req.full_url.endswith("speaker=1") else b"{}"

            return Resp()

        with (
            patch.object(provider, "is_available", return_value=True),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
        ):
            out = tmp_path / "out.wav"
            result = provider.synthesize("テスト", out)
        assert result == out
        assert out.read_bytes() == wav_bytes


class TestAudioPlugin:
    def test_plugin_initializes(self):
        plugin = AudioPlugin()
        assert plugin.initialize() is True
        assert plugin.is_available() is True
        assert plugin.get_provider() is not None

    def test_plugin_shutdown(self):
        plugin = AudioPlugin()
        plugin.initialize()
        plugin.shutdown()
        assert plugin.is_available() is False
        assert plugin.get_provider() is None

    def test_plugin_config_passthrough(self):
        plugin = AudioPlugin(voicevox_url="http://localhost:59999", fallback_mode="skip")
        plugin.initialize()
        provider = plugin.get_provider()
        assert provider.base_url == "http://localhost:59999"
        assert provider.fallback_mode == "skip"

    def test_plugin_name(self):
        assert AudioPlugin.name == "audio"


class TestVoicevoxUnavailableError:
    def test_error_raises(self):
        try:
            raise VoicevoxUnavailableError("VOICEVOX server not running")
        except VoicevoxUnavailableError as exc:
            assert "VOICEVOX" in str(exc)
