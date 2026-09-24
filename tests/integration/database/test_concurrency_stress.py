"""Database concurrency stress test to verify no 'database is locked' errors under load."""
import asyncio
import pytest
from src.backend.database.core import DatabaseManager
from src.backend.database.uow import UnitOfWork


def _prepare_db(db_url: str):
    """Create all tables in a sync engine for the given DB URL (like init_db)."""
    import src.backend.database.models  # noqa
    import src.infrastructure.database.models  # noqa
    from src.infrastructure.database.models import Base as InfraBase
    from sqlalchemy import create_engine

    sync_url = db_url
    if "sqlite+aiosqlite" in sync_url:
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif "postgresql+asyncpg" in sync_url:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    engine = create_engine(sync_url)
    InfraBase.metadata.create_all(engine)
    engine.dispose()


class TestDatabaseConcurrency:
    """Test concurrent database access to ensure no locking issues."""

    @pytest.mark.asyncio
    async def test_concurrent_uow_access(self, tmp_path):
        """20個の非同期タスクから同時に UnitOfWork 経由で読み書きし、競合エラーなく完了することを検証."""
        # Use a file-based DB (in-memory DBs are per-connection and would be empty)
        db_file = tmp_path / "concurrency_test.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

        _prepare_db(db_url)
        db_manager = DatabaseManager(db_url)

        async def worker(worker_id: int, results: list):
            """Worker function that performs database operations."""
            try:
                async with UnitOfWork(db_manager) as uow:
                    # Perform a read
                    state = await uow.misc.get_internal_state("test_key")

                    # Perform a write
                    await uow.misc.save_internal_state(
                        f"worker_{worker_id}",
                        f"value_{worker_id}"
                    )

                    # Perform another read to verify
                    verify_state = await uow.misc.get_internal_state(f"worker_{worker_id}")

                    results.append({
                        "worker_id": worker_id,
                        "success": True,
                        "initial_state": state,
                        "written_value": f"value_{worker_id}",
                        "verified_value": verify_state
                    })
            except Exception as e:
                results.append({
                    "worker_id": worker_id,
                    "success": False,
                    "error": str(e)
                })

        # Run 20 concurrent workers (as specified in the plan)
        results: list = []
        tasks = [worker(i, results) for i in range(20)]
        await asyncio.gather(*tasks)

        # Check that all workers succeeded
        failed_workers = [r for r in results if not r["success"]]
        assert len(failed_workers) == 0, f"Failed workers: {failed_workers}"

        # Verify that we have results from all 20 workers
        assert len(results) == 20

        # Verify that all workers were able to read and write successfully
        for result in results:
            assert result["success"] is True
            assert result["verified_value"] == f"value_{result['worker_id']}"

        await db_manager.engine.dispose()

    @pytest.mark.asyncio
    async def test_concurrent_read_write_mixed(self, tmp_path):
        """Mixed read/write operations under concurrency."""
        db_file = tmp_path / "concurrency_mixed_test.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

        _prepare_db(db_url)
        db_manager = DatabaseManager(db_url)

        async def reader(worker_id: int, results: list):
            """Reader worker - mostly reads with occasional writes."""
            try:
                async with UnitOfWork(db_manager) as uow:
                    # Read internal state
                    for i in range(5):  # 5 reads per worker
                        state = await uow.misc.get_internal_state("counter")
                        await asyncio.sleep(0.001)  # Small delay

                    # Occasionally write
                    if worker_id % 5 == 0:  # Every 5th worker writes
                        current = await uow.misc.get_internal_state("counter") or 0
                        await uow.misc.save_internal_state("counter", current + 1)

                    results.append({"worker_id": worker_id, "success": True})
            except Exception as e:
                results.append({"worker_id": worker_id, "success": False, "error": str(e)})

        async def writer(worker_id: int, results: list):
            """Writer worker - mostly writes with occasional reads."""
            try:
                async with UnitOfWork(db_manager) as uow:
                    # Write multiple times
                    for i in range(3):
                        current = await uow.misc.get_internal_state("counter") or 0
                        await uow.misc.save_internal_state("counter", current + 1)
                        await asyncio.sleep(0.001)

                    # Read back
                    final_value = await uow.misc.get_internal_state("counter")
                    results.append({
                        "worker_id": worker_id,
                        "success": True,
                        "final_counter": final_value
                    })
            except Exception as e:
                results.append({"worker_id": worker_id, "success": False, "error": str(e)})

        # Run mixed workload: 10 readers, 10 writers
        results: list = []
        tasks = []
        for i in range(10):
            tasks.append(reader(i, results))
        for i in range(10, 20):
            tasks.append(writer(i, results))

        await asyncio.gather(*tasks)

        # Check results
        failed_workers = [r for r in results if not r["success"]]
        assert len(failed_workers) == 0, f"Failed workers: {failed_workers}"
        assert len(results) == 20

        await db_manager.engine.dispose()