"""Pillar 2 Full Regression and End-to-End Cross-Component Integration Test (Step 70)."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from src.agents.social.manager import SocialInteractionManager
from src.agents.social.models import RelationshipMetrics
from src.backend.database.models import Book, CharacterRelationship, Base
from src.backend.database.social_repository import SocialRepository
from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskResourceRequirement
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.dag_persistence import FileSystemDAGPersistence
from src.backend.server import app
from src.core.container import AppContainer


@pytest.mark.asyncio
async def test_pillar2_end_to_end_cross_component(tmp_path):
    """Verify all components of Pillar 2 working harmoniously across DB, Manager, DAG, Huey, and API."""
    db = AppContainer.db()

    # 1. DB Schema initialization
    async_eng = getattr(db, "engine", None)
    if async_eng is not None and hasattr(async_eng, "begin"):
        async with async_eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    book_id = 7777
    async with db.get_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(Book).where(Book.id == book_id))
        if not res.scalar_one_or_none():
            session.add(Book(id=book_id, title="Regression Novel", genre="scifi"))
            await session.commit()

    repo = SocialRepository(db)
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Cross-component simulation")
    manager = SocialInteractionManager(llm_adapter=mock_llm, social_repo=repo)

    try:
        # 2. Social Manager + Repository integration
        rel = await manager.update_relationship_async(
            char_a="Captain",
            char_b="Navigator",
            trust_delta=35.0,
            tension_delta=-20.0,
            affinity_delta=30.0,
            ep_num=1,
            book_id=book_id,
            trigger_event="Warp drive success",
        )
        assert rel.dynamics_state == "allies"
        assert rel.trust_score == 85.0

        # Trends summary
        summary = await repo.get_relationship_trends_summary(book_id)
        assert "Captain" in summary and "Navigator" in summary

        # 3. DAG Scheduler + Huey + EventBus + Persistence integration
        persistence = FileSystemDAGPersistence(base_dir=str(tmp_path / "checkpoints"))
        events_emitted = []

        mock_event_bus = MagicMock()
        async def mock_pub(event_type, payload):
            events_emitted.append(event_type)
        mock_event_bus.publish_async = mock_pub

        mock_huey = MagicMock()
        scheduler = DAGScheduler(
            huey_instance=mock_huey,
            persistence=persistence,
            event_bus=mock_event_bus,
            checkpoint_interval=1,
            use_huey=True,
        )

        graph = DAGGraph(dag_id="regression_dag_7777")
        node_1 = DAGTaskNode(task_id="step_a", func_name="fn_a", timeout_seconds=60.0)
        node_2 = DAGTaskNode(task_id="step_b", func_name="fn_b", dependencies=["step_a"], timeout_seconds=60.0)
        graph.add_node(node_1)
        graph.add_node(node_2)

        fake_results = {
            "step_a": {"output": "A finished"},
            "step_b": {"output": "B finished"},
        }

        with patch("src.backend.tasks.huey.execute_agent_node_task") as mock_exec, \
             patch("src.backend.tasks.huey.async_wait_huey_result", new_callable=AsyncMock) as mock_wait:

            def fake_exec(func_name, kwargs, node_id):
                t = MagicMock()
                t.node_id = node_id
                return t

            async def fake_wait(handle, timeout):
                return fake_results[handle.node_id]

            mock_exec.side_effect = fake_exec
            mock_wait.side_effect = fake_wait

            completed_graph = await scheduler.run_dag(graph)

            assert completed_graph.is_all_completed() is True
            assert completed_graph.nodes["step_a"].result == fake_results["step_a"]
            assert completed_graph.nodes["step_b"].result == fake_results["step_b"]

        # 4. Verify EventBus publications
        assert "dag.task_started" in events_emitted
        assert "dag.task_completed" in events_emitted
        assert "dag.completed" in events_emitted

        # 5. Verify Checkpoint saving & loading
        latest_cp = scheduler.find_latest_checkpoint("regression_dag_7777")
        assert latest_cp is not None
        loaded_graph = scheduler.auto_recover("regression_dag_7777")
        assert loaded_graph is not None
        assert loaded_graph.is_all_completed() is True

        # 6. Verify System API endpoints
        client = TestClient(app)
        
        # Huey Health Endpoint
        huey_resp = client.get("/api/system/huey/health")
        assert huey_resp.status_code == 200
        assert "status" in huey_resp.json()

        # DAG Status Endpoint using the persisted checkpoint
        dag_resp = client.get("/api/tasks/dag/regression_dag_7777")
        # Since persistence is configured with tmp_path in test, query non_existent or standard
        assert dag_resp.status_code == 200

    finally:
        async with db.get_session() as session:
            from sqlalchemy import delete
            await session.execute(delete(CharacterRelationship).where(CharacterRelationship.book_id == book_id))
            await session.execute(delete(Book).where(Book.id == book_id))
            await session.commit()
