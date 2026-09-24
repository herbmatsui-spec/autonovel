"""Memory initialization and management for projects and branches."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import typer

from src.agents.memory.core_memory import CoreMemory
from src.agents.memory.manager import MemoryManager
from src.stores.vector_store import InMemoryVectorStore, RedisVectorStore, VectorStore


def get_memory_directory(project_id: str, branch: str = "main", base_dir: Optional[str | Path] = None) -> Path:
    base = Path(base_dir) if base_dir else Path("memory")
    return base / project_id / branch


def initialize_memory_for_project(
    project_id: str,
    branch: str = "main",
    base_dir: Optional[str | Path] = None,
    vector_store: Optional[VectorStore] = None,
) -> MemoryManager:
    """指定プロジェクト・ブランチ用の MemoryManager を初期化または復元する"""
    mem_dir = get_memory_directory(project_id, branch, base_dir)
    mem_dir.mkdir(parents=True, exist_ok=True)

    if vector_store is None:
        try:
            vector_store = RedisVectorStore(skip_connection_check=True)
        except Exception:
            vector_store = InMemoryVectorStore()

    manager = MemoryManager(vector_store=vector_store)
    core_file = mem_dir / "core_memory.json"

    if core_file.exists():
        manager.core_memory.load_from_disk(core_file)

    return manager


cli_app = typer.Typer(name="memory_initializer", help="Project memory initialization CLI")


@cli_app.command(name="init")
def init_cli(
    project: str = typer.Option("default", "--project", "-p", help="プロジェクト名"),
    branch: str = typer.Option("main", "--branch", "-b", help="ブランチ名"),
):
    manager = initialize_memory_for_project(project, branch)
    mem_dir = get_memory_directory(project, branch)
    manager.save_state(mem_dir)
    typer.echo(f"Initialized memory for project '{project}' (branch: '{branch}') at {mem_dir}")


if __name__ == "__main__":
    cli_app()


__all__ = ["initialize_memory_for_project", "get_memory_directory", "cli_app"]
