"""Unit tests for BranchMemoryManager."""
from src.agents.memory.branch_manager import BranchMemoryManager
from src.agents.memory.core_memory import CoreMemory


def test_fork_and_compare(tmp_path):
    bm = BranchMemoryManager(project_id="test_branch_proj", base_dir=tmp_path)

    # 1. main ブランチ作成
    main_mem = CoreMemory()
    main_mem.update_emotion("A", "B", "affection", 0.8)
    bm.save_branch("main", main_mem)

    # 2. IF ブランチ fork
    if_mem = bm.fork_branch("main", "if_betrayal")
    assert if_mem.character_emotions["A->B"]["affection"] == 0.8

    # 3. IF ブランチで感情変更
    if_mem.update_emotion("A", "B", "affection", -0.9)  # 嫌悪反転
    bm.save_branch("if_betrayal", if_mem)

    # 4. 比較
    diff = bm.compare_branches("main", "if_betrayal")
    assert diff["differences_count"] == 1
    assert "A->B" in diff["differences"]
    assert diff["differences"]["A->B"]["main"]["affection"] == 0.8
    assert diff["differences"]["A->B"]["if_betrayal"]["affection"] == -0.1
