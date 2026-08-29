#!/usr/bin/env python3
"""tests/load/test_consistency_perf.py - 整合性チェック性能測定"""
import time
import statistics
from src.consistency.engine import ConsistencyEngine
from src.consistency.checkers import get_default_checkers
from src.consistency.checkers.base import CheckContext
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs, WORKSPACE_ROOT
from src.filesystem_memory.writer import write_file


def setup_test_data(book_id: int, num_chapters: int = 100):
    base = get_workspace_path(book_id, 1)
    ensure_workspace_dirs(base)
    for i in range(1, num_chapters + 1):
        write_file(
            base / f"memory/chapters/chapter_{i:02d}.md",
            f"第{i}章の内容。" * 20 + " 魔王の伏線。" + " 太郎は果敢に突撃した。" * 10,
        )
    # STORY_SUMMARY
    from src.filesystem_memory.writer import write_file
    write_file(
        get_workspace_path(book_id, 1) / "STORY_SUMMARY.md",
        "# あらすじ\n## 未回収要素\n- 魔王の再臨\n- 幼馴染の秘密",
    )
    # WORLD
    write_file(
        get_workspace_path(book_id, 1) / "WORLD.md",
        '# 世界観\n```json\n{"prohibited": ["魔法"]}\n```',
    )
    # CHARACTERS
    write_file(
        get_workspace_path(book_id, 1) / "CHARACTERS.md",
        "## 主人公\n- 名前: 太郎\n- 性格: 臆病",
    )


def measure_checks(book_id: int, runs: int = 10) -> list:
    engine = ConsistencyEngine(get_default_checkers())
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        engine.run(CheckContext(book_id=book_id, branch_id=1))
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


if __name__ == "__main__":
    import sys
    print("Setting up test data...")
    # Use a temp dir
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        os.environ["WORKSPACE_ROOT"] = tmpdir  # Not used by our paths module
        # Instead, monkey-patch
        import src.filesystem_memory.paths as paths_module
        original_root = paths_module.WORKSPACE_ROOT
        paths_module.WORKSPACE_ROOT = Path(tmpdir) / "ws"
        try:
            setup_test_data(999, num_chapters=100)
            print("Measuring...")
            times = measure_checks(999, runs=10)
            print(f"Min: {min(times)*1000:.1f}ms")
            print(f"Max: {max(times)*1000:.1f}ms")
            print(f"Mean: {statistics.mean(times)*1000:.1f}ms")
            print(f"Median: {statistics.median(times)*1000:.1f}ms")
            if len(times) > 1:
                print(f"Stdev: {statistics.stdev(times)*1000:.1f}ms")
        finally:
            paths_module.WORKSPACE_ROOT = original_root