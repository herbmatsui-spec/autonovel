import io
import wave
from typing import Optional


class AudioCombiner:
    """Pure Python WAV結合モジュール。
    複数WAVクリップ間に無音ポーズ（セリフ間0.4秒等）を挿入して1本の通し朗読WAVに結合する (Step 14)。
    可変ポーズ対応版 (Step 42)。
    """

    @staticmethod
    def combine_wav_clips(
        clips: list[bytes],
        silence_duration_sec: float = 0.4,
        pauses: Optional[list[float]] = None,
    ) -> bytes:
        """クリップを可変ポーズで結合。
        
        Args:
            clips: WAVバイト列のリスト
            silence_duration_sec: デフォルト無音時間（秒）
            pauses: 各クリップ間の無音時間リスト（clips - 1 個の要素）。Noneの場合はsilence_duration_secを使用。
        """
        valid_clips = [c for c in clips if c and c.startswith(b"RIFF")]
        if not valid_clips:
            return b""

        out_buf = io.BytesIO()
        try:
            with wave.open(io.BytesIO(valid_clips[0]), "rb") as first_wav:
                params = first_wav.getparams()
                nchannels = params.nchannels
                sampwidth = params.sampwidth
                framerate = params.framerate

            with wave.open(out_buf, "wb") as out_wav:
                out_wav.setparams(params)
                for i, clip in enumerate(valid_clips):
                    with wave.open(io.BytesIO(clip), "rb") as in_wav:
                        out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
                    
                    # 最後のクリップでない場合、ポーズを挿入
                    if i < len(valid_clips) - 1:
                        if pauses and i < len(pauses):
                            pause_sec = pauses[i]
                        else:
                            pause_sec = silence_duration_sec
                        
                        if pause_sec > 0:
                            silence_frames = int(framerate * pause_sec)
                            silence_data = b"\x00" * (silence_frames * nchannels * sampwidth)
                            out_wav.writeframes(silence_data)

            return out_buf.getvalue()
        except Exception:
            # 万一フォーマット異常がある場合は最初のクリップをフォールバックとして返す
            return valid_clips[0]
