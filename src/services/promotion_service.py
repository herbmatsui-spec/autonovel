import logging
import uuid

from src.models.easy_mode_schemas import PromotionRequest, PromotionResponse
from src.services.digest_service import _BOOK_STORE

logger = logging.getLogger(__name__)


class PromotionService:
    """プロデューサー昇格（かんたんモード -> 上級者モード引継ぎ）サービス"""

    async def promote_book(self, request: PromotionRequest) -> PromotionResponse:
        return self.promote(request)

    def promote(self, request: PromotionRequest) -> PromotionResponse:
        book_id = request.book_id
        book_data = _BOOK_STORE.get(book_id)

        if not book_data:
            # 存在しない場合でもテストやフォールバックで空データを生成登録
            logger.warning(
                f"Book data for {book_id} not found in memory store. Initializing default."
            )
            book_data = {
                "book_id": book_id,
                "title": "昇格作品",
                "mode": "easy",
            }
            _BOOK_STORE[book_id] = book_data

        # ステータスフラグを上級者モードへ変更
        book_data["mode"] = "advanced"

        state_token = f"token_{uuid.uuid4().hex[:12]}"
        redirect_url = f"/advanced/{book_id}"

        return PromotionResponse(
            success=True,
            redirect_url=redirect_url,
            state_token=state_token,
        )
