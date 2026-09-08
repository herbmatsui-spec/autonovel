"""High-load Stress and Benchmark Script for Social Dynamics and DAGScheduler (Steps 63-64)."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.social.models import RelationshipMetrics
from src.backend.database.models import CharacterRelationship
from src.backend.database.social_repository import SocialRepository
from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskResourceRequirement
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.core.container import AppContainer


async def benchmark_social_repository(num_pairs: int = 15, history_per_pair: int = 5) -> float:
    """Benchmark high-throughput writes and cleanup in SocialRepository."""
    print(f"--- Benchmarking SocialRepository ({num_pairs} pairs, {history_per_pair} updates each) ---")
    start = time.perf_counter()

    db = AppContainer.db()
    
    # Ensure tables exist in the db engine via async run_sync
    from src.backend.database.models import Base
    async_eng = getattr(db, "engine", None)
    if async_eng is not None and hasattr(async_eng, "begin"):
        async with async_eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    repo = SocialRepository(db)
    book_id = 9999

    from src.backend.database.models import Book
    async with db.get_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(Book).where(Book.id == book_id))
        if not res.scalar_one_or_none():
            session.add(Book(id=book_id, title="Benchmark Novel", genre="fantasy"))
            await session.commit()

    try:
        # Seed relationships
        for i in range(num_pairs):
            metrics = RelationshipMetrics(
                char_a=f"Hero_{i}",
                char_b=f"Villain_{i}",
                affinity_score=50.0,
                trust_score=50.0,
                tension_score=20.0,
                depth=35.0,
                dynamics_state="neutral",
                last_interaction_ep=1,
            )
            await repo.upsert_relationship(
                book_id=book_id,
                char_a=f"Hero_{i}",
                char_b=f"Villain_{i}",
                metrics=metrics,
            )

        # Retrieve saved relationships
        saved_rels = await repo.get_all_relationships(book_id)
        assert len(saved_rels) >= num_pairs

        # Append historical updates
        for ep in range(1, history_per_pair + 1):
            for (char_a, char_b), m in saved_rels.items():
                if char_a >= char_b:
                    continue
                updated_metrics = RelationshipMetrics(
                    char_a=char_a,
                    char_b=char_b,
                    affinity_score=m.affinity_score + ep,
                    trust_score=m.trust_score + (ep * 0.5),
                    tension_score=m.tension_score + (ep * 2),
                    dynamics_state="developing",
                    last_interaction_ep=ep,
                )
                await repo.record_history(
                    book_id=book_id,
                    char_a=char_a,
                    char_b=char_b,
                    episode_num=ep,
                    metrics=updated_metrics,
                    trigger_event=f"Event in ep {ep}",
                )

        first_pair = [p for p in saved_rels.keys() if p[0] < p[1]][0]
        history = await repo.get_relationship_history(book_id, first_pair[0], first_pair[1])
        assert len(history) == history_per_pair

        deleted = await repo.cleanup_old_history(book_id=book_id, keep_latest_per_pair=2)
        print(f"Cleaned up {deleted} old history rows beyond 2 episodes.")

        duration = time.perf_counter() - start
        print(f"SocialRepository benchmark completed in {duration:.3f}s")
        return duration
    finally:
        # Cleanup benchmark data
        async with db.get_session() as session:
            from sqlalchemy import delete
            await session.execute(delete(CharacterRelationship).where(CharacterRelationship.book_id == book_id))
            await session.execute(delete(Book).where(Book.id == book_id))
            await session.commit()


async def benchmark_dag_scheduler(num_tasks: int = 30) -> float:
    """Benchmark DAGScheduler concurrency with backpressure."""
    print(f"--- Benchmarking DAGScheduler ({num_tasks} tasks) ---")
    start = time.perf_counter()

    graph = DAGGraph(dag_id="bench_dag")
    for i in range(num_tasks):
        node = DAGTaskNode(
            task_id=f"task_{i}",
            func_name="work_item",
            kwargs={"idx": i},
            priority=i % 5,
            resources=TaskResourceRequirement(cpu_cores=1.0, ram_mb=512),
        )
        if i > 0 and i % 5 != 0:
            node.dependencies.append(f"task_{i-1}")
        graph.add_node(node)

    async def work_item(idx: int):
        await asyncio.sleep(0.01)
        return f"result_{idx}"

    scheduler = DAGScheduler(task_registry={"work_item": work_item})
    executed = await scheduler.run_dag(graph, max_concurrency=4)

    assert executed.is_all_completed()
    assert scheduler.active_allocations.cpu_cores == 0.0

    duration = time.perf_counter() - start
    print(f"DAGScheduler benchmark completed in {duration:.3f}s")
    return duration


async def main():
    repo_time = await benchmark_social_repository(num_pairs=15, history_per_pair=5)
    dag_time = await benchmark_dag_scheduler(num_tasks=25)
    print("\n==========================================")
    print("All benchmarks finished successfully!")
    print(f"Repo time: {repo_time:.3f}s | DAG time: {dag_time:.3f}s")
    print("==========================================")


if __name__ == "__main__":
    asyncio.run(main())
