"""VOICEVOX 音声合成プロバイダのプラグイン化 (Step 20).

VOICEVOX サーバー不在時の Graceful Fallback（空ファイル生成またはスキップ）
を実装する。コアパイプラインは VOICEVOX が無くても完結する。
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_VOICEVOX_URL = "http://localhost:50021"
DEFAULT_SPEAKER = 1
_QUERY_TIMEOUT = 3.0
_SYNTH_TIMEOUT = 10.0


class VoicevoxUnavailableError(Exception):
    """VOICEVOX サーバーが利用できない場合の例外。"""


class VoicevoxProvider:
    """VOICEVOX 音声合成プロバイダ（Graceful Fallback 付き）.

    - :meth:`is_available`: VOICEVOX サーバーへの接続確認
    - :meth:`synthesize`: テキストを WAV に合成。サーバー不在時は
      ``fallback_mode`` に応じてスキップ（None）または空ファイル生成
    """

    def __init__(
        self,
        base_url: str | None = None,
        speaker: int = DEFAULT_SPEAKER,
        fallback_mode: str = "skip",
    ) -> None:
        self.base_url = (base_url or DEFAULT_VOICEVOX_URL).rstrip("/")
        self.speaker = speaker
        self.fallback_mode = fallback_mode  # "skip" or "empty_file"

    # -------------------------------------------------- 可用性

    def is_available(self) -> bool:
        """VOICEVOX サーバーが起動しているか確認する。"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/version", method="GET"
            )
            with urllib.request.urlopen(req, timeout=_QUERY_TIMEOUT):
                return True
        except (urllib.error.URLError, OSError):
            return False

    # -------------------------------------------------- 合成

    def synthesize(self, text: str, output_path: Path, **options: Any) -> Path | None:
        """テキストを WAV に合成する。

        Args:
            text: 合成するテキスト。
            output_path: 出力 WAV パス。
            **options: speaker 等の上書きオプション。

        Returns:
            生成した WAV パス。VOICEVOX 不在時はフォールバック動作に従い
            None（スキップ）または空ファイルのパスを返す。
        """
        speaker = int(options.get("speaker", self.speaker))
        if not self.is_available():
            return self._fallback(output_path)

        try:
            # 1) audio_query で韻律情報を取得
            query_url = (
                f"{self.base_url}/audio_query?text={urllib.parse.quote(text)}"
                f"&speaker={speaker}"
            )
            req = urllib.request.Request(query_url, method="POST")
            with urllib.request.urlopen(req, timeout=_QUERY_TIMEOUT) as resp:
                query_json = resp.read()

            # 2) synthesis で WAV を生成
            synth_url = f"{self.base_url}/synthesis?speaker={speaker}"
            req = urllib.request.Request(
                synth_url,
                data=query_json,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=_SYNTH_TIMEOUT) as resp:
                audio_data = resp.read()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_data)
            logger.info("Voicevox synthesized: %s", output_path)
            return output_path
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("Voicevox synthesis failed, falling back: %s", exc)
            return self._fallback(output_path)

    # -------------------------------------------------- フォールバック

    def _fallback(self, output_path: Path) -> Path | None:
        """サーバー不在時の Graceful Fallback.

        - fallback_mode == "empty_file": 空の WAV ファイルを生成して返す
        - fallback_mode == "skip": None を返してパイプラインにスキップさせる
        """
        if self.fallback_mode == "empty_file":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # 最小限のヘッダを持つ無音 WAV (1 sample) を生成
            import io
            import struct
            import wave

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(struct.pack("<h", 0))
            output_path.write_bytes(buf.getvalue())
            logger.info("Voicevox fallback: wrote silent WAV %s", output_path)
            return output_path
        logger.info("Voicevox fallback: skipping synthesis for %s", output_path)
        return None
