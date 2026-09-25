"""音声合成プラグイン (Step 20).

VOICEVOX 等の音声合成をオプショナルプラグインとして提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from src.interfaces.plugin import BasePlugin

logger = logging.getLogger(__name__)


class AudioPlugin(BasePlugin):
    """音声合成機能（VOICEVOX 等）のオプショナルプラグイン."""

    name = "audio"

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        self._provider: Any = None

    def initialize(self) -> bool:
        """VoicevoxProvider を初期化する。依存不足でも False を返しコアを妨げない。"""
        try:
            from src.plugins.audio.voicevox import VoicevoxProvider
        except Exception as exc:  # noqa: BLE001
            logger.warning("AudioPlugin disabled (import failed): %s", exc)
            return False
        self._provider = VoicevoxProvider(
            base_url=self.config.get("voicevox_url"),
            speaker=int(self.config.get("speaker", 1)),
            fallback_mode=str(self.config.get("fallback_mode", "skip")),
        )
        self._initialized = True
        logger.info("AudioPlugin initialized")
        return True

    def is_available(self) -> bool:
        """プロバイダが束ね済みか。"""
        return self._initialized and self._provider is not None

    def get_provider(self) -> Any:
        """VoicevoxProvider を返す。未初期化時は None。"""
        if not self.is_available():
            return None
        return self._provider

    def shutdown(self) -> None:
        self._provider = None
        self._initialized = False
