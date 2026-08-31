"""SQLAlchemy を用いた作品データアクセスを集約するリポジトリ層。"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.models.book import Bible, Book, Chapter, Character, Plot
from src.models.task import Task


class BookRepository:
    """
    作品データへのアクセスを抽象化するリポジトリ。
    SQLAlchemy Session を使用して DB 操作を行う。
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_book(self, book_id: int) -> Book | None:
        """指定した ID の作品情報を取得する"""
        return self.session.get(Book, book_id)

    def create_task(self, status: str = "pending", result: str | None = None) -> Task:
        """Create a new Task record and return it."""
        now = int(time.time())
        task = Task(status=status, result=result, created_at=now, updated_at=now)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_task(self, task_id: int) -> Task | None:
        """指定した ID のタスクを取得する"""
        return self.session.get(Task, task_id)

    def update_task_status(self, task_id: int, status: str) -> None:
        """タスクのステータスを更新する"""
        task = self.session.get(Task, task_id)
        if task:
            task.status = status
            task.updated_at = int(time.time())
            self.session.commit()

    def set_task_result(self, task_id: int, result: str) -> None:
        """タスクの結果を保存し、ステータスを completed に更新する"""
        task = self.session.get(Task, task_id)
        if task:
            task.result = result
            task.updated_at = int(time.time())
            task.status = "completed"
            self.session.commit()

    def delete_task(self, task_id: int) -> None:
        """Delete a task record from the database."""
        task = self.session.get(Task, task_id)
        if task:
            self.session.delete(task)
            self.session.commit()

    def get_all_non_anchor_chapters(
        self, book_id: int, branch_id: int = 1, order_by: str = "ep_num"
    ) -> list[Chapter]:
        """
        指定した作品・ブランチの、アンカーではない章をすべて取得する。
        """
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
            select(Bible)
            .where(Bible.book_id == book_id)
            .order_by(desc(Bible.created_at))
            .limit(1)
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


__all__: list[str] = ["BookRepository", "Any"]
