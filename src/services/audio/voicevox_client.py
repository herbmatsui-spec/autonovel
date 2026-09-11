import logging
import httpx
from src.services.audio.base import (
    AudioSynthesisClient,
    AudioSynthesisRequest,
    AudioSynthesisResult,
)

logger = logging.getLogger(__name__)


class VoicevoxClient(AudioSynthesisClient):
    """VOICEVOX HTTP APIクライアント。
    ローカルまたはリモートの VOICEVOX サーバー (/audio_query, /synthesis) と通信する。
    """

    def __init__(self, base_url: str = "http://localhost:50021", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def synthesize(self, req: AudioSynthesisRequest | None) -> AudioSynthesisResult:
        if req is None or not req.text:
            return AudioSynthesisResult(audio_bytes=b"", format="wav", duration_seconds=0.0)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            # 1. 音声クエリ生成
            query_res = await client.post(
                "/audio_query",
                params={"text": req.text, "speaker": req.speaker_id},
            )
            query_res.raise_for_status()
            query_data = query_res.json()

            # パラメータ反映
            query_data["speedScale"] = req.speed_scale
            query_data["pitchScale"] = req.pitch_scale
            query_data["intonationScale"] = req.intonation_scale

            # 2. 音声合成実行
            synth_res = await client.post(
                "/synthesis",
                params={"speaker": req.speaker_id},
                json=query_data,
            )
            synth_res.raise_for_status()
            audio_bytes = synth_res.content

            # 推定再生時間 (目安)
            duration = max(0.5, len(req.text) * 0.15 / max(0.5, req.speed_scale))

            return AudioSynthesisResult(
                audio_bytes=audio_bytes,
                format="wav",
                duration_seconds=duration,
                sample_rate=24000,
            )
