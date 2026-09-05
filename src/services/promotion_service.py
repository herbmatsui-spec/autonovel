import logging
import secrets
from datetime import datetime, timedelta, timezone

from src.domain.entities.easy_mode import PromotionRequest, PromotionResponse

logger = logging.getLogger("producer_handoff")

STATE_TOKEN_TTL_HOURS = 24


def _build_redirect_url(book_id: str) -> str:
    """クライアントが遷移すべき Studio モードの URL を組み立てる。"""
    return f"/studio/{book_id}"


def build_state_token() -> str:
    """URL-safe な state_token を発行する (PromotionService からも利用可)。"""
    return secrets.token_urlsafe(16)


class PromotionService:
    """かんたんモード → 上級者モードへの作品引き継ぎサービス [Producer Handoff]。

    ``db`` に DatabaseManager を渡すと Book.mode を ``'easy'`` → ``'advanced'`` に更新する。
    対応する Draft が見つからない場合は ValueError を raise（router 層で 404 に変換）。
    state_token には暗号論的に安全な secrets.token_urlsafe を使い、InternalState テーブルに
    ``promotion_token_<book_id>`` キーで TTL (24h) 付きで保存する。
    """

    def __init__(self, db=None):
        self._db = db

    async def save_state_token(self, book_id: str, token: str) -> None:
        """state_token を InternalState に保存 (TTL 24h)。

        PromotionService 単体テストからも検証可能とするため副作用を最小化する。
        db が利用できない環境では no-op。
        """
        if self._db is None:
            logger.debug("[producer-handoff] db=None: skipping state_token save for %s", book_id)
            return

        from src.backend.database.models import InternalState

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=STATE_TOKEN_TTL_HOURS)).isoformat()
        key = f"promotion_token_{book_id}"

        async with self._db.get_session() as session:
            existing = await session.execute(
                InternalState.__table__.select().where(InternalState.key == key)
            )
            row = existing.fetchone()
            if row is None:
                await session.execute(
                    InternalState.__table__.insert().values(key=key, value=f"{token}|{expires_at}")
                )
            else:
                await session.execute(
                    InternalState.__table__.update()
                    .where(InternalState.key == key)
                    .values(value=f"{token}|{expires_at}", updated_at=func.now())
                )
            await session.commit()

    async def promote_book(self, request: PromotionRequest) -> PromotionResponse:
        book_id = request.book_id

        state_token = build_state_token()

        if self._db is None:
            logger.warning(
                "[producer-handoff] db=None: skipping Book.mode update for %s",
                book_id,
            )
            return PromotionResponse(
                success=True,
                redirect_url=_build_redirect_url(book_id),
                state_token=state_token,
            )

        from sqlalchemy import func

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

            # state_token を InternalState に永続化 (TTL 24h)
            from src.backend.database.models import InternalState

            expires_at = (
                datetime.now(timezone.utc) + timedelta(hours=STATE_TOKEN_TTL_HOURS)
            ).isoformat()
            key = f"promotion_token_{book_id}"
            existing = await session.execute(
                InternalState.__table__.select().where(InternalState.key == key)
            )
            row = existing.fetchone()
            payload = f"{state_token}|{expires_at}"
            if row is None:
                await session.execute(
                    InternalState.__table__.insert().values(key=key, value=payload)
                )
            else:
                await session.execute(
                    InternalState.__table__.update()
                    .where(InternalState.key == key)
                    .values(value=payload, updated_at=func.now())
                )

            await session.commit()

        redirect_url = _build_redirect_url(book_id)

        return PromotionResponse(
            success=True,
            redirect_url=redirect_url,
            state_token=state_token,
        )
