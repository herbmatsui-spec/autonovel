from typing import Optional

from src.services.llm_service import LLMService


class BibleExtractor:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def extract(self, book_id: int, content: str, reporter=None) -> Optional[dict]:
        """
        Bible抽出トリガー。
        現在はスタブ実装だが、将来的には内容からBible情報を抽出する。
        
        Args:
            book_id: 書籍ID
            content: 抽出対象の本文
            reporter: オプションのレポーター
            
        Returns:
            抽出されたBible情報の辞書、またはNone
        """
        # 現在はスタブ実装
        return None
