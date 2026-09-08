"""Comprehensive Health Check and Diagnostics for Pillar 2 (State & Async Infra)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backend.tasks.huey import check_huey_health
from src.backend.database.core import DatabaseManager
from src.core.container import AppContainer
from src.backend.tasks.resource_manager import ResourceManager
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.database.social_repository import SocialRepository


async def run_pillar2_diagnostics() -> dict[str, bool]:
    results = {}
    print("==================================================")
    print("      PILLAR 2 HEALTH & DIAGNOSTICS CHECK        ")
    print("==================================================")

    # 1. Huey Task Queue Check
    huey_health = check_huey_health()
    huey_ok = huey_health.get("status") == "healthy"
    results["Huey Queue"] = huey_ok
    print(f"[*] Huey Queue Health: {'[OK]' if huey_ok else '[WARN/FAIL]'} ({huey_health.get('storage')})")

    # 2. Database Connection Check
    try:
        db = AppContainer.db()
        async with db.get_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        results["Database Connectivity"] = True
        print("[*] Database Connectivity: [OK]")
    except Exception as e:
        results["Database Connectivity"] = False
        print(f"[!] Database Connectivity: [FAIL] ({e})")

    # 3. Social Dynamics Schema Check
    try:
        from scripts.migrate_social_db import check_and_create_tables
        schema_ok = check_and_create_tables()
        results["Social Schema"] = schema_ok
        print(f"[*] Social Tables Schema: {'[OK]' if schema_ok else '[FAIL]'}")
    except Exception as e:
        results["Social Schema"] = False
        print(f"[!] Social Tables Schema: [FAIL] ({e})")

    # 4. Resource Manager Check
    try:
        rm = ResourceManager()
        limits = rm.calculate_worker_pool_limits()
        results["Resource Manager"] = limits["max_parallel_tasks"] > 0
        print(f"[*] Resource Limits: [OK] (Max Parallel Tasks: {limits['max_parallel_tasks']}, Image: {limits['image_workers']})")
    except Exception as e:
        results["Resource Manager"] = False
        print(f"[!] Resource Manager: [FAIL] ({e})")

    # 5. DAG Scheduler Instantiation Check
    try:
        sched = DAGScheduler()
        results["DAG Scheduler"] = sched is not None
        print("[*] DAG Scheduler Engine: [OK]")
    except Exception as e:
        results["DAG Scheduler"] = False
        print(f"[!] DAG Scheduler Engine: [FAIL] ({e})")

    print("==================================================")
    all_passed = all(results.values())
    print(f"Overall Pillar 2 Status: {'HEALTHY [ALL PASS]' if all_passed else 'DEGRADED'}")
    print("==================================================")
    return results


if __name__ == "__main__":
    res = asyncio.run(run_pillar2_diagnostics())
    sys.exit(0 if all(res.values()) else 1)
