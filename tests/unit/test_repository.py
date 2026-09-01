"""リポジトリ層のユニットテスト。"""
from __future__ import annotations

import pytest
from src.backend.database.repository import BookRepository


def test_get_book(real_db_manager):
    repo = BookRepository(real_db_manager)
    book = repo.get_book(book_id=1)
    assert book is None


def test_create_task(real_db_manager):
    repo = BookRepository(real_db_manager)
    task = repo.create_task(task_id="test-1", status="pending")
    assert task.id == "test-1"
    assert task.status == "pending"


def test_get_task(real_db_manager):
    repo = BookRepository(real_db_manager)
    repo.create_task(task_id="test-2", status="running")
    task = repo.get_task("test-2")
    assert task is not None
    assert task.status == "running"


def test_update_task_status(real_db_manager):
    repo = BookRepository(real_db_manager)
    repo.create_task(task_id="test-3", status="pending")
    repo.update_task_status("test-3", "completed")
    task = repo.get_task("test-3")
    assert task is not None
    assert task.status == "completed"


def test_set_task_result(real_db_manager):
    repo = BookRepository(real_db_manager)
    repo.create_task(task_id="test-4", status="pending")
    repo.set_task_result("test-4", "some result")
    task = repo.get_task("test-4")
    assert task is not None
    assert task.result == "some result"
    assert task.status == "completed"


def test_delete_task(real_db_manager):
    repo = BookRepository(real_db_manager)
    repo.create_task(task_id="test-5", status="pending")
    repo.delete_task("test-5")
    task = repo.get_task("test-5")
    assert task is None


def test_get_all_non_anchor_chapters(real_db_manager):
    repo = BookRepository(real_db_manager)
    chapters = repo.get_all_non_anchor_chapters(book_id=1)
    assert isinstance(chapters, list)


def test_get_all_characters(real_db_manager):
    repo = BookRepository(real_db_manager)
    characters = repo.get_all_characters(book_id=1)
    assert isinstance(characters, list)


def test_get_latest_bible(real_db_manager):
    repo = BookRepository(real_db_manager)
    bible = repo.get_latest_bible(book_id=1)
    assert bible is None


def test_get_all_plots(real_db_manager):
    repo = BookRepository(real_db_manager)
    plots = repo.get_all_plots(book_id=1, branch_id=1)
    assert isinstance(plots, list)