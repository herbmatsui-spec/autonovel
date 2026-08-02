import logging
from typing import Any, ClassVar, Dict, List, Optional

from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EngineService:
    """アプリケーションの中心的なビジネスロジックを担うサービス。
    現段階では以下のメソッドを提供し、簡易的なデータ操作と Gemini 呼び出しを行う。
    将来的には DB リポジトリ層へ委譲する予定。
    """

    _instance: ClassVar[Optional["EngineService"]] = None

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        self.llm = LLMService(api_key=self.api_key)
        # 簡易インメモリ書籍リスト（後で DB に置き換える）
        self._books: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls, api_key: Optional[str] = None) -> "EngineService":
        """EngineServiceのシングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls(api_key)
        elif api_key and not cls._instance.api_key:
            cls._instance.api_key = api_key
        return cls._instance

    # ---------------------------------------------------------------------
    # 書籍管理（簡易スタブ）
    # ---------------------------------------------------------------------
    def create_book(self, title: str, genre: str, target_eps: int) -> Dict[str, Any]:
        new_id = len(self._books) + 1
        book = {"id": new_id, "title": title, "genre": genre, "target_eps": target_eps, "stress": 0}
        self._books.append(book)
        logger.info(f"Created book {new_id}: {title}")
        return book

    def get_all_books(self) -> List[Dict[str, Any]]:
        return list(self._books)

    def get_book_details(self, book_id: int) -> Optional[Dict[str, Any]]:
        for b in self._books:
            if b["id"] == book_id:
                # ダミーデータで stress と空プロットリスト返却
                return {"book": b, "stress": b.get("stress", 0), "plots": []}
        return None

    def delete_book(self, book_id: int) -> bool:
        for i, b in enumerate(self._books):
            if b["id"] == book_id:
                del self._books[i]
                logger.info(f"Deleted book {book_id}")
                return True
        return False

    @property
    def engine(self):
        return self.llm

    async def generate_plot(self, prompt: str) -> Dict[str, Any]:
        """LLM にプロット生成プロンプトを投げ、JSON 結果を取得する。"""
        result = await self.llm.generate_json(
            purpose="planning",
            prompt=prompt,
            response_schema=None,
        )
        return result
