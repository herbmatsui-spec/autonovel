import io
import wave
from src.services.audio.base import (
    AudioSynthesisClient,
    AudioSynthesisRequest,
    AudioSynthesisResult,
)


class MockAudioSynthesisClient(AudioSynthesisClient):
    """オフライン・テスト用モック音声クライアント。
    指定秒数の無音WAVバイナリをオンメモリ生成して返す。
    """

    def __init__(self, sample_rate: int = 24000, default_duration: float = 0.5):
        self.sample_rate = sample_rate
        self.default_duration = default_duration

    async def synthesize(self, req: AudioSynthesisRequest | None) -> AudioSynthesisResult:
        duration = self.default_duration
        if req and req.text:
            # 文字数に応じて微調整 (10文字につき約0.5秒)
            duration = max(0.2, len(req.text) * 0.05)

        num_channels = 1
        sampwidth = 2  # 16-bit PCM
        framerate = self.sample_rate
        num_frames = int(framerate * duration)
        raw_data = b"\x00" * (num_frames * num_channels * sampwidth)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            wav_file.writeframes(raw_data)

        audio_bytes = buf.getvalue()
        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_seconds=duration,
            sample_rate=self.sample_rate,
        )
