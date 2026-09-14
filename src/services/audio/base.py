from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AudioSynthesisRequest:
    text: str
    speaker_id: int = 3  # デフォルト: ずんだもん(ノーマル)または四国めたん
    speed_scale: float = 1.0
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    volume_scale: float = 1.0


@dataclass
class AudioSynthesisResult:
    audio_bytes: bytes
    format: str = "wav"
    duration_seconds: float = 0.0
    sample_rate: int = 24000


class AudioSynthesisClient(ABC):
    @abstractmethod
    async def synthesize(self, req: AudioSynthesisRequest | None) -> AudioSynthesisResult:
        pass
