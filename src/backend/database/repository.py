from __future__ import annotations

"""
database/repository.py - UoWコンテキストを自動解決する DataRepository ファサード
"""
import json
import time
from typing import Any

from sqlalchemy import desc, select

from src.backend.database.core import DatabaseManager, SessionLocal
from src.backend.database.models import Bible, Book, Chapter, Character, Plot
from src.infrastructure.database.models.task import Task

from .uow_context import current_uow


class DataRepositoryFacade:
    """
    既存の engine_agents 等が `self.repo` 経由で各メソッドを呼び出せるようにするための後方互換ファサード。
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def __getattr__(self, name):
        async def wrapper(*args, **kwargs):
            import logging

            log = logging.getLogger("debug.uow_flow")
            uow = current_uow.get()
            log.debug(f"Calling {name} - UoW Context: {'Exists' if uow else 'None'}")
            if uow:
                for repo_attr in [
                    "books",
                    "plots",
                    "chapters",
                    "characters",
                    "branches",
                    "bible",
                    "misc",
                    "rules",
                    "audit",
                    "prompt_versions",
                    "illustrations",
                ]:
                    repo = getattr(uow, repo_attr)
                    if hasattr(repo, name):
                        log.debug(f"Resolved {name} via UoW {repo_attr}")
                        return await getattr(repo, name)(*args, **kwargs)
                raise AttributeError(f"DataRepositoryFacade (UoW mode) has no attribute '{name}'")
            else:
                log.warning(
                    f"No UoW context for {name}. Falling back to Auto mode (New Transaction)."
                )
                from .uow import UnitOfWork

                async with UnitOfWork(self.db) as temp_uow:
                    for repo_attr in [
                        "books",
                        "plots",
                        "chapters",
                        "characters",
                        "branches",
                        "bible",
                        "misc",
                        "rules",
                        "audit",
                        "prompt_versions",
                    ]:
                        repo = getattr(temp_uow, repo_attr)
                        if hasattr(repo, name):
                            return await getattr(repo, name)(*args, **kwargs)
                    raise AttributeError(
                        f"DataRepositoryFacade (Auto mode) has no attribute '{name}'"
                    )

        return wrapper

    async def get_state(self, key: str, default: Any = None) -> Any:
        from src.backend.database.models import InternalState

        with self.db.get_session() as session:
            state = session.query(InternalState).filter_by(key=key).one_or_none()
            if not state:
                return default
            try:
                return json.loads(state.value)
            except Exception:
                return state.value

    async def set_state(self, key: str, value: Any) -> None:
        from src.backend.database.models import InternalState

        with self.db.get_session() as session:
            state = session.query(InternalState).filter_by(key=key).one_or_none()
            if not state:
                state = InternalState(key=key)
                session.add(state)
            state.value = (
                json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            )
            state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            session.commit()


# DataRepository をエイリアスとして公開
DataRepository = DataRepositoryFacade


class BookRepository:
    """
    作品データおよびタスク管理へのアクセスを抽象化するリポジトリ。
    同期セッションまたは DatabaseManager を受け付けて操作を行う。
    """

    def __init__(self, session_or_db: Any = None) -> None:
        if isinstance(session_or_db, DatabaseManager):
            self.session = SessionLocal()
            self._db = session_or_db
        elif hasattr(session_or_db, "execute") or hasattr(session_or_db, "get"):
            self.session = session_or_db
            self._db = None
        else:
            self.session = SessionLocal()
            self._db = None

    def _safe_commit(self) -> None:
        """同期・非同期どちらのセッションでも安全にコミットする"""
        import asyncio
        import inspect

        res = self.session.commit()
        if inspect.isawaitable(res):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(res)
                else:
                    loop.run_until_complete(res)
            except Exception:
                pass

    def _safe_refresh(self, instance: Any) -> None:
        """同期・非同期どちらのセッションでも安全にリフレッシュする"""
        import asyncio
        import inspect

        res = self.session.refresh(instance)
        if inspect.isawaitable(res):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(res)
                else:
                    loop.run_until_complete(res)
            except Exception:
                pass

    def get_book(self, book_id: int) -> Book | None:
        """指定した ID の作品情報を取得する"""
        return self.session.get(Book, book_id)

    def create_task(
        self, task_id: str | None = None, status: str = "pending", result: str | None = None
    ) -> Task:
        """Create a new Task record and return it."""
        now = int(time.time())
        if not task_id:
            import uuid

            task_id = str(uuid.uuid4())
        task = Task(id=task_id, status=status, result=result, created_at=now, updated_at=now)
        self.session.add(task)
        self._safe_commit()
        self._safe_refresh(task)
        return task

    def get_task(self, task_id: str) -> Task | None:
        """指定した ID のタスクを取得する"""
        return self.session.get(Task, task_id)

    def update_task_status(self, task_id: str, status: str) -> None:
        """タスクのステータスを更新する"""
        task = self.session.get(Task, task_id)
        if task:
            task.status = status
            task.updated_at = int(time.time())
            self._safe_commit()

    def set_task_result(self, task_id: str, result: str) -> None:
        """タスクの結果を保存し、ステータスを completed に更新する"""
        task = self.session.get(Task, task_id)
        if task:
            task.result = result
            task.updated_at = int(time.time())
            task.status = "completed"
            self._safe_commit()

    def delete_task(self, task_id: str) -> None:
        """Delete a task record from the database."""
        task = self.session.get(Task, task_id)
        if task:
            self.session.delete(task)
            self._safe_commit()

    def get_all_non_anchor_chapters(
        self, book_id: int, branch_id: int = 1, order_by: str = "ep_num"
    ) -> list[Chapter]:
        """指定した作品・ブランチの、アンカーではない章をすべて取得する。"""
        stmt = (
            select(Chapter)
            .where(Chapter.book_id == book_id)
            .where(Chapter.is_anchor.is_(False))
            .order_by(getattr(Chapter, order_by))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_all_characters(self, book_id: int) -> list[Character]:
        """指定した作品に紐づくキャラクターをすべて取得する"""
        stmt = select(Character).where(Character.book_id == book_id)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_latest_bible(self, book_id: int) -> Bible | None:
        """指定した作品の最新の世界観設定（Bible）を取得する"""
        stmt = (
            select(Bible).where(Bible.book_id == book_id).order_by(desc(Bible.created_at)).limit(1)
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_all_plots(self, book_id: int, branch_id: int = 1) -> list[Plot]:
        """指定した作品・ブランチのプロットをすべて取得する"""
        stmt = (
            select(Plot)
            .where(Plot.book_id == book_id)
            .where(Plot.branch_id == branch_id)
            .order_by(Plot.ep_num)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def save_or_update_book_with_chapter(
        self,
        book_id: int,
        title: str = "R15ファンタジー作品",
        genre: str = "ファンタジー (R15)",
        chapter_text: str = "",
        character_params: dict | None = None,
        plots: list | None = None,
    ) -> Book:
        """かんたんモード等のデータをDBに新規作成または更新保存する"""
        book = self.get_book(book_id)
        if not book:
            book = Book(
                id=book_id,
                title=title,
                genre=genre,
                concept="かんたんモード生成作品",
                synopsis=chapter_text[:200] if chapter_text else "",
                target_eps=10,
            )
            self.session.add(book)
            self._safe_commit()
            self._safe_refresh(book)

        # 第1話の更新または作成
        if chapter_text:
            stmt = select(Chapter).where(Chapter.book_id == book_id).where(Chapter.ep_num == 1)
            chapter = self.session.execute(stmt).scalar_one_or_none()
            if chapter:
                chapter.content = chapter_text
                chapter.summary = chapter_text[:100]
            else:
                chapter = Chapter(
                    book_id=book_id,
                    ep_num=1,
                    title="第1話 運命の覚醒",
                    content=chapter_text,
                    summary=chapter_text[:100],
                )
                self.session.add(chapter)

        # キャラクターの登録/更新
        if character_params and character_params.get("name"):
            char_name = character_params["name"]
            stmt = (
                select(Character)
                .where(Character.book_id == book_id)
                .where(Character.name == char_name)
            )
            char = self.session.execute(stmt).scalar_one_or_none()
            if char:
                char.personality = character_params.get("personality", "")
                char.ability = character_params.get("ability", "")
            else:
                char = Character(
                    book_id=book_id,
                    name=char_name,
                    role="主人公",
                    personality=character_params.get("personality", ""),
                    ability=character_params.get("ability", ""),
                )
                self.session.add(char)

        self._safe_commit()
        return book


# Re-export individual repositories for compatibility
from .repositories.audit import AuditRepository  # noqa: E402
from .repositories.bible import BibleRepository  # noqa: E402
from .repositories.book import BookRepository as AsyncBookRepository  # noqa: E402
from .repositories.chapter import ChapterRepository  # noqa: E402
from .repositories.character import CharacterRepository  # noqa: E402
from .repositories.narrative_metrics_repo import NarrativeMetricRepository  # noqa: E402
from .repositories.plot import PlotRepository  # noqa: E402

__all__ = [
    "DataRepositoryFacade",
    "DataRepository",
    "BookRepository",
    "AsyncBookRepository",
    "ChapterRepository",
    "CharacterRepository",
    "PlotRepository",
    "BibleRepository",
    "AuditRepository",
    "NarrativeMetricRepository",
]
