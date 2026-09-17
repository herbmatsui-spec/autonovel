"""AudioTtsAdapter 抽象基底インターフェース (v5.0 Step 7).

常駐VOICEVOXコンテナ（数GBメモリ消費）を廃止し、
外部オンデマンド従量API（OpenAI TTS, ElevenLabs等）へ移行するための基底クラス。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TtsRequest:
    """音声合成リクエストパラメータ。"""

    text: str
    voice_id: str = "default"
    speed: float = 1.0
    format: str = "mp3"


@dataclass
class TtsResult:
    """音声合成結果。"""

    audio_bytes: bytes
    format: str = "mp3"
    provider: str = "mock"
    cost_usd: float = 0.0
    character_count: int = 0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class AudioTtsAdapter(ABC):
    """従量課金TTS音声合成プロバイダ基底クラス。"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー識別子 (例: "openai_tts", "elevenlabs", "mock")"""
        pass

    @abstractmethod
    async def synthesize(self, request: TtsRequest) -> TtsResult:
        """テキストから音声を合成しバイトデータと消費コストを返す。"""
        pass
