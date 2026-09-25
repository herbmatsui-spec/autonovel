"""MultimediaService のプラグインカプセル化 (Step 17).

コアバックエンドから :class:`MultimediaService` をオプショナルプラグインとして
切り離す。`require_multimedia()` で毎回例外を投げるのではなく、
プラグインレジストリで有効時のみルーターにマウントする。
"""

from __future__ import annotations

import logging
from typing import Any

from src.interfaces.plugin import BasePlugin

logger = logging.getLogger(__name__)


class MultimediaPlugin(BasePlugin):
    """マルチメディア機能（画像・音声・EPUB）を束ねるオプショナルプラグイン.

    PluginProtocol に従い、ENABLE_MULTIMEDIA フラグが有効な場合のみ
    PluginRegistry によってロードされる。
    """

    name = "multimedia"

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        self._service: Any = None

    def initialize(self) -> bool:
        """MultimediaService を遅延束ねして初期化する。

        依存モジュールのインポートに失敗した場合も ``False`` を返し、
        コア起動を妨げない。
        """
        try:
            from src.backend.multimedia_service import MultimediaService
        except Exception as exc:  # noqa: BLE001 - オプショナル依存は握りつぶす
            logger.warning("MultimediaPlugin disabled (import failed): %s", exc)
            return False
        self._service = MultimediaService
        self._initialized = True
        logger.info("MultimediaPlugin initialized")
        return True

    def is_available(self) -> bool:
        """MultimediaService が束ね済みで利用可能か。"""
        return self._initialized and self._service is not None

    def get_service_class(self) -> Any:
        """束ねた MultimediaService クラスを返す。未初期化時は None。"""
        if not self.is_available():
            return None
        return self._service

    def shutdown(self) -> None:
        """プラグインを終了し、束ねたサービス参照を解放する。"""
        self._service = None
        self._initialized = False
        logger.info("MultimediaPlugin shut down")
