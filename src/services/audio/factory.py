import os
from src.backend.config import settings
from src.services.audio.base import AudioSynthesisClient
from src.services.audio.mock_client import MockAudioSynthesisClient
from src.services.audio.voicevox_client import VoicevoxClient

_client_cache: dict[str, AudioSynthesisClient] = {}


def get_audio_client(provider_type: str | None = None) -> AudioSynthesisClient:
    """音声合成クライアントファクトリ。
    provider_type: 'mock' | 'voicevox' (Noneの場合は設定・環境変数から自動解決)
    """
    resolved_type = provider_type
    if not resolved_type:
        if getattr(settings, "ENABLE_AUDIO_SYNTH", False) or os.getenv("ENABLE_AUDIO_SYNTH", "").lower() in ("true", "1"):
            resolved_type = "voicevox"
        else:
            resolved_type = "mock"

    if resolved_type in _client_cache:
        return _client_cache[resolved_type]

    if resolved_type == "voicevox":
        voicevox_url = getattr(settings, "VOICEVOX_URL", "http://localhost:50021")
        timeout = getattr(settings, "VOICEVOX_TIMEOUT_SECONDS", 30.0)
        client = VoicevoxClient(base_url=voicevox_url, timeout=timeout)
    else:
        client = MockAudioSynthesisClient()

    _client_cache[resolved_type] = client
    return client
