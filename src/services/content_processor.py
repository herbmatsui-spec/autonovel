import logging

logger = logging.getLogger(__name__)

class ContentProcessor:
    """コンテンツ加工サービス"""
    def sanitize(self, content: str) -> str:
        return content

    def apply_tone(self, content: str, tone: str) -> str:
        return content
