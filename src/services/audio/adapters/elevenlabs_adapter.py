"""OpenAI TTS & ElevenLabs オンデマンド従量課金音声合成アダプタ (v5.0 Step 8).

常駐VOICEVOXコンテナ不要で、1,000文字あたり約$0.015（約2.2円）の従量課金で
高品位な朗読音声を生成する。
"""
from __future__ import annotations

from typing import Optional

import httpx

from src.services.audio.adapters.base import (
    AudioTtsAdapter,
    TtsRequest,
    TtsResult,
)


class OpenAIttsAdapter(AudioTtsAdapter):
    """OpenAI TTS オンデマンド従量APIアダプタ（標準: $0.015 / 1k文字）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    @property
    def provider_name(self) -> str:
        return "openai_tts"

    async def synthesize(self, request: TtsRequest) -> TtsResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "tts-1",
            "input": request.text,
            "voice": request.voice_id if request.voice_id != "default" else "alloy",
            "speed": request.speed,
            "response_format": request.format,
        }

        if self._client is not None:
            resp = await self._client.post(
                f"{self.base_url}/audio/speech",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            audio_bytes = resp.content
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/audio/speech",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                audio_bytes = resp.content

        char_len = len(request.text)
        cost = (char_len / 1000.0) * 0.015
        return TtsResult(
            audio_bytes=audio_bytes,
            format=request.format,
            provider="openai_tts",
            cost_usd=cost,
            character_count=char_len,
        )


class ElevenLabsAdapter(AudioTtsAdapter):
    """ElevenLabs オンデマンド従量APIアダプタ（標準: 約$0.030 / 1k文字）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.elevenlabs.io/v1",
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize(self, request: TtsRequest) -> TtsResult:
        voice_id = request.voice_id if request.voice_id != "default" else "21m00Tcm4TlvDq8ikWAM"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": request.text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        url = f"{self.base_url}/text-to-speech/{voice_id}"

        if self._client is not None:
            resp = await self._client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio_bytes = resp.content
        else:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                audio_bytes = resp.content

        char_len = len(request.text)
        cost = (char_len / 1000.0) * 0.030
        return TtsResult(
            audio_bytes=audio_bytes,
            format=request.format,
            provider="elevenlabs",
            cost_usd=cost,
            character_count=char_len,
        )
