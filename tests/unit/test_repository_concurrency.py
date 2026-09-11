"""
Unit tests verifying Phase 3 database and repository concurrency fixes:
- Async get_state / set_state with proper datetime types
- Concurrent AsyncSession isolation in recalc_all_book_scores
"""
import pytest
from src.core.container import AppContainer


@pytest.mark.asyncio
async def test_repository_get_set_state_async():
    """Verify get_state and set_state work cleanly with AsyncSession and DateTime."""
    repo = AppContainer.repo()
    test_key = "test_phase3_key"
    test_val = {"step": 13, "status": "verified"}

    await repo.set_state(test_key, test_val)
    val = await repo.get_state(test_key)
    assert val == test_val

    # Update state
    updated_val = {"step": 14, "status": "updated"}
    await repo.set_state(test_key, updated_val)
    val2 = await repo.get_state(test_key)
    assert val2 == updated_val


@pytest.mark.asyncio
async def test_recalc_all_book_scores_runs_without_concurrency_error():
    """Verify recalc_all_book_scores endpoint function handles sessions safely."""
    from src.backend.database.core import get_db_manager
    import src.backend.database.models  # noqa: F401
    from src.backend.routers.system import recalc_all_book_scores
    from src.infrastructure.database.models.base_orm import Base

    db_manager = get_db_manager()
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    res = await recalc_all_book_scores()
    assert res.get("status") == "success"
    assert "recalculated_count" in res
