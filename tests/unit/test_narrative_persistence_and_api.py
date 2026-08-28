"""
tests/unit/test_narrative_persistence_and_api.py - Phase 4: 永続化および API エンドポイントのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.backend.database.models import Base, InternalState
from src.backend.database.repositories.misc import MiscRepository, save_narrative, load_narrative
from src.backend.routers.narrative import router as narrative_router


@pytest.mark.asyncio
async def test_narrative_repository_save_and_load():
    """ステップ 22: MiscRepository での NarrativeState ハブの save / load テスト"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    hub_data = {
        "book_id": 55,
        "branch_id": 1,
        "episodes": {"1": {"char_count": 1200, "tension": 0.8}},
        "tension_curve": [0.8],
        "affinity_map": {"ヒロイン": 75.0},
        "foreshadow_registry": [],
        "continuity_violations": [],
        "quality_scores": {"1": {"coherence": 0.95}},
        "erotic_metrics": {"1": {"score": 85.0}},
        "narrative_scores": {"1": {"overall": 90.0}},
    }

    async with async_session() as session:
        repo = MiscRepository(session)
        await repo.save_narrative(55, 1, hub_data)
        await session.commit()

    async with async_session() as session:
        repo = MiscRepository(session)
        loaded = await repo.load_narrative(55, 1)
        assert loaded is not None
        assert loaded["book_id"] == 55
        assert loaded["tension_curve"] == [0.8]
        assert loaded["affinity_map"]["ヒロイン"] == 75.0
        assert loaded["episodes"]["1"]["char_count"] == 1200

    # スタンドアロン関数のテスト
    async with async_session() as session:
        loaded_func = await load_narrative(55, 1, session=session)
        assert loaded_func == loaded

    await engine.dispose()


@pytest.mark.asyncio
async def test_narrative_api_endpoint():
    """ステップ 23: GET /api/narrative/{book_id}/{branch_id} エンドポイントのテスト"""
    mock_hub_dict = {
        "book_id": 42,
        "branch_id": 1,
        "episodes": {1: {"tension": 0.9}},
        "tension_curve": [0.9],
        "affinity_map": {"メインヒロイン": 90.0},
        "foreshadow_registry": [],
        "continuity_violations": [],
        "quality_scores": {},
        "erotic_metrics": {},
        "narrative_scores": {},
    }

    app = FastAPI()
    app.include_router(narrative_router)

    with patch("src.backend.routers.narrative.UnitOfWork") as mock_uow_cls:
        mock_uow = MagicMock()
        mock_uow.misc.load_narrative = AsyncMock(return_value=mock_hub_dict)
        mock_uow_cls.return_value.__aenter__.return_value = mock_uow
        mock_uow_cls.return_value.__aexit__.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/narrative/42/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["book_id"] == 42
            assert data["tension_curve"] == [0.9]
            assert data["affinity_map"]["メインヒロイン"] == 90.0


@pytest.mark.asyncio
async def test_narrative_api_endpoint_empty_fallback():
    """ステップ 23: データ未存在時のデフォルトハブ返却テスト"""
    app = FastAPI()
    app.include_router(narrative_router)

    with patch("src.backend.routers.narrative.UnitOfWork") as mock_uow_cls:
        mock_uow = MagicMock()
        mock_uow.misc.load_narrative = AsyncMock(return_value=None)
        mock_uow_cls.return_value.__aenter__.return_value = mock_uow
        mock_uow_cls.return_value.__aexit__.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/narrative/999/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["book_id"] == 999
            assert data["branch_id"] == 1
            assert data["episodes"] == {}
