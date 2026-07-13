import asyncio
import os
import tempfile

import pytest
from sqlalchemy import text

from src.backend.database.core import DatabaseManager, init_db


@pytest.mark.asyncio
async def test_concurrent_write_load():
    # 1. テスト用の一時的なDBファイルを作成
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        # DBの初期化
        init_db(db_path)
        db_url = f'sqlite+aiosqlite:///{db_path}'
        manager = DatabaseManager(db_url)

        # テスト用テーブルの作成
        async with manager.get_session() as session:
            async with session.begin():
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS load_test (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        val TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))

        # 2. 同時書き込み処理の定義
        async def write_worker(worker_id, iterations=20):
            # 各ワーカーが独自のセッションを持つことで、接続競合をシミュレート
            for i in range(iterations):
                try:
                    async with manager.get_session() as session:
                        async with session.begin():
                            await session.execute(
                                text("INSERT INTO load_test (val) VALUES (:v)"),
                                {"v": f"worker_{worker_id}_iter_{i}"}
                            )
                except Exception as e:
                    # ここで "database is locked" が発生しないかを確認
                    pytest.fail(f"Worker {worker_id} encountered an error: {e}")

        # 3. 複数のワーカーを同時に実行 (10ワーカー x 20回 = 200書き込み)
        num_workers = 10
        iterations_per_worker = 20
        workers = [write_worker(i, iterations_per_worker) for i in range(num_workers)]

        await asyncio.gather(*workers)

        # 4. 最終的なデータ件数を確認
        async with manager.get_session() as session:
            result = await session.execute(text("SELECT count(*) as count FROM load_test"))
            count = result.scalar()

        assert count == num_workers * iterations_per_worker
        print(f"Successfully wrote {count} records concurrently without lock errors.")

    finally:
        # クリーンアップ
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except Exception:
                pass
