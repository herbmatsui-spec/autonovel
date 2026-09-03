import logging
import secrets

from src.domain.entities.easy_mode import PromotionRequest, PromotionResponse

logger = logging.getLogger("producer_handoff")


class PromotionService:
    """かんたんモード → 上級者モードへの作品引き継ぎサービス [Producer Handoff]。

    ``db`` に DatabaseManager を渡すと Book.mode を ``'easy'`` → ``'advanced'`` に更新する。
    対応する Draft が見つからない場合は ValueError を raise（router 層で 404 に変換）。
    state_token には暗号論的に安全な secrets.token_urlsafe を使う。
    """

    def __init__(self, db=None):
        self._db = db

    async def promote_book(self, request: PromotionRequest) -> PromotionResponse:
        book_id = request.book_id

        if self._db is None:
            logger.warning(
                "[producer-handoff] db=None: skipping Book.mode update for %s",
                book_id,
            )
            state_token = secrets.token_urlsafe(16)
            return PromotionResponse(
                success=True,
                redirect_url=f"/advanced/{book_id}",
                state_token=state_token,
            )

        from src.backend.database.models import Book
        from src.backend.database.repositories import EasyModeDraftRepository

        async with self._db.get_session() as session:
            repo = EasyModeDraftRepository(session)
            draft_json = await repo.load_digest(book_id)
            if draft_json is None:
                raise ValueError(f"Book draft not found: {book_id}")

            db_book_id = draft_json.get("db_book_id")
            if db_book_id is not None:
                result = await session.execute(Book.__table__.select().where(Book.id == db_book_id))
                book_row = result.fetchone()
                if book_row is None:
                    raise ValueError(f"Book record not found for db_book_id={db_book_id}")
                await session.execute(
                    Book.__table__.update().where(Book.id == db_book_id).values(mode="advanced")
                )
                await session.commit()

        state_token = secrets.token_urlsafe(16)
        redirect_url = f"/advanced/{book_id}"

        return PromotionResponse(
            success=True,
            redirect_url=redirect_url,
            state_token=state_token,
        )
