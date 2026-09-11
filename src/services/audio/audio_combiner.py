import io
import wave


class AudioCombiner:
    """Pure Python WAV結合モジュール。
    複数WAVクリップ間に無音ポーズ（セリフ間0.4秒等）を挿入して1本の通し朗読WAVに結合する (Step 14)。
    """

    @staticmethod
    def combine_wav_clips(clips: list[bytes], silence_duration_sec: float = 0.4) -> bytes:
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

            silence_frames = int(framerate * silence_duration_sec)
            silence_data = b"\x00" * (silence_frames * nchannels * sampwidth)

            with wave.open(out_buf, "wb") as out_wav:
                out_wav.setparams(params)
                for i, clip in enumerate(valid_clips):
                    with wave.open(io.BytesIO(clip), "rb") as in_wav:
                        out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
                    if i < len(valid_clips) - 1 and silence_frames > 0:
                        out_wav.writeframes(silence_data)

            return out_buf.getvalue()
        except Exception:
            # 万一フォーマット異常がある場合は最初のクリップをフォールバックとして返す
            return valid_clips[0]
