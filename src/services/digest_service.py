"""ダイジェスト生成サービスおよび章処理ユーティリティ [Quick Digest]."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from src.domain.entities.easy_mode import (
    DigestRequest,
    DigestResponse,
    DigestStatus,
)
from src.services.llm_service import LLMService

logger = logging.getLogger("quick_digest")

CHAPTER_MAX_LENGTH = 1500


def process_chapter(chapter: str) -> str:
    """章本文から主要テキストを抽出する。"""
    return (
        (chapter[:CHAPTER_MAX_LENGTH].rstrip() + "...")
        if len(chapter) > CHAPTER_MAX_LENGTH
        else chapter
    )


class DigestService:
    """ファスト・ダイジェスト生成サービス [Quick Digest]。

    永続化対応: ``db`` に DatabaseManager を渡して DB に保存する。
    ``db=None`` は許可しない。
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        db: Any = None,
    ):
        if db is None:
            raise ValueError(
                "DigestService requires db=DatabaseManager (in-memory store removed in v2)."
            )
        self.llm_service = llm_service or LLMService()
        self._db = db

    async def _load_gacha_from_db(self, request_id: str) -> dict | None:
        from src.backend.database.repositories import EasyModeDraftRepository

        async with self._db.get_session() as session:
            repo = EasyModeDraftRepository(session)
            return await repo.load_gacha_plans(request_id)

    async def _create_book_record(self, title: str) -> int | None:
        """新規 Book レコードを DB に作成し、整数 ID を返す。"""
        from src.backend.database.models import Book

        async with self._db.get_session() as session:
            book = Book(
                title=title,
                mode="easy",
                status="draft",
            )
            session.add(book)
            await session.flush()
            await session.commit()
            return book.id

    async def _save_digest_db(
        self,
        draft_id: str,
        parent_request_id: str,
        digest_json: dict,
        db_book_id: int | None,
    ) -> None:
        from src.backend.database.repositories import EasyModeDraftRepository

        async with self._db.get_session() as session:
            repo = EasyModeDraftRepository(session)
            await repo.save_digest(draft_id, parent_request_id, digest_json)
            if db_book_id is not None:
                book = await repo.get(db_book_id)
                if book is not None:
                    book.mode = "easy"
            await session.commit()

    async def create_digest(self, request: DigestRequest) -> DigestResponse:
        return await self.generate_digest(request)

    async def generate_digest(self, request: DigestRequest) -> DigestResponse:
        """選択された企画から高速でプロット・第1話・クライマックスプレビューを生成する"""
        gacha_data: dict | None = await self._load_gacha_from_db(request.request_id)

        selected_plan = None

        if gacha_data:
            plans = gacha_data.get("response", {}).get("plans", [])
            for p in plans:
                if p.get("plan_id") == request.selected_plan_id:
                    selected_plan = p
                    break

        if not selected_plan:
            selected_plan = {
                "title": "選択された物語",
                "logline": "運命に立ち向かう主人公の冒険譚",
                "protagonist_summary": "強い意志を持った主人公",
                "charm_point": "圧倒的カタルシス",
            }

        title = selected_plan.get("title", "無題の物語")
        draft_id = f"book_{uuid.uuid4().hex[:8]}"
        db_book_id: int | None = None
        digest_json: dict = {}

        db_book_id = await self._create_book_record(title)

        try:
            synopsis_prompt = f"""
タイトル: {title}
キャッチコピー: {selected_plan.get("logline")}
主人公: {selected_plan.get("protagonist_summary")}

上記作品の全体あらすじ（300文字程度）と全10話の章構成プロットを作成してください。
"""
            synopsis_text = await self.llm_service.generate_text(
                purpose="planning",
                prompt=synopsis_prompt,
            )

            ep1_prompt = f"""
タイトル: {title}
全体概要: {synopsis_text[:200]}

小説の「第1話」本文（1000文字〜1500文字程度）を執筆してください。
"""
            climax_prompt = f"""
タイトル: {title}
全体概要: {synopsis_text[:200]}

物語のクライマックス（見せ場）のプレビュー描写（800文字程度）を執筆してください。
"""

            ep1_task = self.llm_service.generate_text(purpose="writing", prompt=ep1_prompt)
            climax_task = self.llm_service.generate_text(purpose="climax", prompt=climax_prompt)

            ep1_text, climax_text = await asyncio.gather(ep1_task, climax_task)

            response = DigestResponse(
                book_id=draft_id,
                title=title,
                synopsis=synopsis_text,
                episode_1_text=ep1_text,
                climax_preview_text=climax_text,
                status=DigestStatus.COMPLETED,
            )
            digest_json = response.model_dump()

        except Exception as e:
            logger.error(f"[quick-digest] Digest generation failed for book_id {draft_id}: {e}")
            response = DigestResponse(
                book_id=draft_id,
                title=title,
                synopsis="生成中にエラーが発生しましたが、基本枠組みは作成されました。",
                episode_1_text="第1話の生成に失敗しました。再試行してください。",
                climax_preview_text="クライマックスプレビューの生成に失敗しました。",
                status=DigestStatus.FAILED,
            )
            digest_json = response.model_dump()

        finally:
            await self._save_digest_db(draft_id, request.request_id, digest_json, db_book_id)

        return response

    async def generate_suggestions(self, chapter: str) -> list[str]:
        """章本文から LLM で意味的な提案を生成する (実 LLM 呼び出し)。"""
        if not chapter:
            return ["続行: (空章のため先頭から再開)", "調査が必要な未確認な要素を指摘"]

        try:
            prompt = (
                "以下の章本文から、執筆を継続するための提案を 2-3 個、簡潔な日本語で"
                "出力してください。各提案は 1 行 (40 文字以内) で。\n\n"
                f"--- 章本文 ---\n{chapter[:800]}\n--- 提案 ---"
            )
            res = await self.llm_service.generate_text(
                purpose="suggestions",
                prompt=prompt,
            )
            lines = [ln.strip("- ・*").strip() for ln in (res or "").splitlines() if ln.strip()]
            if not lines:
                return [f"続行: {chapter[:100]}…", "調査が必要な未確認な要素を指摘"]
            return lines[:3]
        except Exception as e:  # noqa: BLE001
            logger.warning("generate_suggestions LLM call failed: %s", e)
            return [f"続行: {chapter[:100]}…", "調査が必要な未確認な要素を指摘"]


# ----------------------------------------------------------------------
# テスト互換のモジュールレベル関数
# ----------------------------------------------------------------------


class _DummyDB:
    """DigestService が要求する最小限の DB インタフェース。
    テストでは DB が実際に使用されないため，空の async コンテキストマネージャだけを提供する。
    """

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def commit(self):  # pragma: no cover
            pass

        async def flush(self):  # pragma: no cover
            pass

        def add(self, *_):  # pragma: no cover
            pass

    async def get_session(self):
        return self._DummySession()


async def generate_suggestions(chapter: str) -> list[str]:
    """テストが期待するモジュールレベル関数。
    内部で最小限のダミー DB を用意し，DigestService のインスタンスを生成して
    メソッドを委譲するだけ。
    """
    dummy_db = _DummyDB()
    service = DigestService(llm_service=LLMService(), db=dummy_db)  # type: ignore[arg-type]
    return await service.generate_suggestions(chapter)


__all__ = ["process_chapter", "DigestService", "generate_suggestions"]
