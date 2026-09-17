"""音声合成クライアント＆アダプタファクトリ (v5.0 Step 9).

常駐VOICEVOXコンテナ（メモリ数GB消費）を任意化・廃止し、
オンデマンドの外部従量APIアダプタ（OpenAI TTS / ElevenLabs / Mock）へ一本化する。
"""
from __future__ import annotations

import os
from typing import Optional

from src.backend.config import settings
from src.services.audio.adapters.base import AudioTtsAdapter, TtsRequest, TtsResult
from src.services.audio.adapters.elevenlabs_adapter import (
    ElevenLabsAdapter,
    OpenAIttsAdapter,
)
from src.services.audio.base import AudioSynthesisClient
from src.services.audio.mock_client import MockAudioSynthesisClient
from src.services.audio.voicevox_client import VoicevoxClient


# ── v5.0 新TTS従量APIアダプタ ──

class MockTtsAdapter(AudioTtsAdapter):
    """テスト・開発用モックTTSアダプタ（コスト0円・即時応答）。"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def synthesize(self, request: TtsRequest) -> TtsResult:
        return TtsResult(
            audio_bytes=b"RIFFdummyWAVEfmt",
            format=request.format,
            provider="mock",
            cost_usd=0.0,
            character_count=len(request.text),
        )


def get_tts_adapter(provider: str | None = None) -> AudioTtsAdapter:
    """外部従量APIベースのTTSアダプタを取得する。

    Args:
        provider: "mock", "openai" ("openai_tts"), "elevenlabs" など

    Returns:
        AudioTtsAdapter 実装インスタンス
    """
    if provider is None:
        provider = os.getenv("TTS_PROVIDER", "mock").lower()
    else:
        provider = provider.lower()

    if provider in ("openai", "openai_tts"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        return OpenAIttsAdapter(api_key=api_key)
    elif provider in ("elevenlabs", "eleven_labs"):
        api_key = os.getenv("ELEVENLABS_API_KEY", "") or os.getenv("XI_API_KEY", "")
        return ElevenLabsAdapter(api_key=api_key)
    else:
        return MockTtsAdapter()


# ── 後方互換性レガシークライアント ──

_client_cache: dict[str, AudioSynthesisClient] = {}


def get_audio_client(provider_type: str | None = None) -> AudioSynthesisClient:
    """旧インターフェース (AudioSynthesisClient) 互換用ファクトリ。"""
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
