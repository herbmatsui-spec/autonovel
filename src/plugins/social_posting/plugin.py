"""外部投稿プラグイン.

なろう・カクヨム等への外部投稿をオプショナルプラグインとして提供する。
"""

from __future__ import annotations

import logging

from src.interfaces.plugin import BasePlugin

logger = logging.getLogger(__name__)


class SocialPostingPlugin(BasePlugin):
    """外部投稿機能のオプショナルプラグイン（デフォルト無効）."""

    name = "social_posting"

    def initialize(self) -> bool:
        """外部投稿は認証情報が必要。未設定時は False を返す。"""
        if not self.config.get("narou_cookie") and not self.config.get("kakuyomu_cookie"):
            logger.info("SocialPostingPlugin disabled (no credentials configured)")
            return False
        self._initialized = True
        return True

    def is_available(self) -> bool:
        return self._initialized

    def shutdown(self) -> None:
        self._initialized = False
