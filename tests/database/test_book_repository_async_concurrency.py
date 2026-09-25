"""
tests/database/test_book_repository_async_concurrency.py
Part 1 (Step 1-4) リグレッション防止テスト:
BookRepository の非同期セッション操作、明示的コミット待機、並行アクセス安全性を検証。
"""

import asyncio
from contextlib import asynccontextmanager
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.infrastructure.database.models import Base
from src.backend.database.repository import BookRepository


@asynccontextmanager
async def create_test_db():
    """テスト用インメモリ SQLite DB とセッションファクトリを提供するヘルパー"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_book_repository_async_commit_waits_for_completion():
    """AsyncSession を渡した BookRepository が is_async=True となり、非同期コミットが待機されることを確認"""
    async with create_test_db() as session_factory:
        async with session_factory() as session:
            repo = BookRepository(session)
            assert repo.is_async is True

            # 非同期タスク作成
            task = await repo.create_task_async(task_id="task-async-1", status="running")
            assert task.id == "task-async-1"
            assert task.status == "running"

            # 即座に DB から取得して永続化されていることを確認
            fetched = await repo.get_task_async("task-async-1")
            assert fetched is not None
            assert fetched.id == "task-async-1"
            assert fetched.status == "running"


@pytest.mark.asyncio
async def test_create_and_update_task_status_async():
    """非同期でのタスク作成、ステータス更新、結果設定、削除が安全に行えることを確認"""
    async with create_test_db() as session_factory:
        async with session_factory() as session:
            repo = BookRepository(session)

            # 1. 作成
            await repo.create_task_async(task_id="task-crud-1", status="pending")

            # 2. ステータス更新
            await repo.update_task_status_async("task-crud-1", "running")
            task = await repo.get_task_async("task-crud-1")
            assert task.status == "running"

            # 3. 結果設定
            await repo.set_task_result_async("task-crud-1", '{"progress": 100}')
            task = await repo.get_task_async("task-crud-1")
            assert task.status == "completed"
            assert task.result == '{"progress": 100}'

            # 4. 削除
            await repo.delete_task_async("task-crud-1")
            deleted = await repo.get_task_async("task-crud-1")
            assert deleted is None


@pytest.mark.asyncio
async def test_save_or_update_book_with_chapter_async():
    """非同期での作品・第1話・キャラクター保存が安全に行えることを確認"""
    async with create_test_db() as session_factory:
        async with session_factory() as session:
            repo = BookRepository(session)

            book = await repo.save_or_update_book_with_chapter_async(
                book_id=None,
                title="非同期テスト勇者譚",
                genre="異世界ファンタジー",
                chapter_text="第1話のテスト本文です。静かな朝、勇者は立ち上がった。",
                character_params={"name": "アレン", "personality": "勇敢", "ability": "聖剣技"},
            )
            assert book.id is not None
            assert book.title == "非同期テスト勇者譚"

            # 取得検証
            fetched_book = await repo.get_book_async(book.id)
            assert fetched_book is not None
            assert fetched_book.title == "非同期テスト勇者譚"


@pytest.mark.asyncio
async def test_book_repository_concurrency():
    """複数セッションによる並行タスク作成・更新がデッドロックなく完了することを検証 (Step 4)"""
    async with create_test_db() as session_factory:
        async def worker(worker_id: int):
            async with session_factory() as session:
                repo = BookRepository(session)
                task_id = f"concurrent-task-{worker_id}"
                await repo.create_task_async(task_id=task_id, status="pending")
                await repo.update_task_status_async(task_id, "completed")
                task = await repo.get_task_async(task_id)
                assert task is not None
                assert task.status == "completed"

        # 10並行ワーカーを実行
        tasks = [worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
