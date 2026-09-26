"""Unit tests for memory tools."""
from src.agents.memory.manager import MemoryManager
from src.agents.tools.memory_tools import MEMORY_TOOLS_SCHEMA, execute_memory_tool


def test_update_emotion_tool():
    manager = MemoryManager()
    assert len(MEMORY_TOOLS_SCHEMA) == 7

    res = execute_memory_tool(
        "update_emotion",
        {"source": "A", "target": "B", "emotion": "fear", "delta": 0.4, "reason": "danger"},
        manager,
    )
    assert res["success"] is True
    assert res["new_value"] == 0.4
    assert manager.core_memory.character_emotions["A->B"]["fear"] == 0.4

    # 取得ツールもテスト
    res_get = execute_memory_tool(
        "get_emotional_context",
        {"source": "A", "target": "B"},
        manager,
    )
    assert res_get["success"] is True
    assert res_get["context"]["fear"] == 0.4


def test_active_hook_and_note_tools():
    manager = MemoryManager()
    res_hook = execute_memory_tool(
        "set_active_hook",
        {"hook": "resolve_rivalry"},
        manager,
    )
    assert res_hook["success"] is True
    assert "resolve_rivalry" in manager.core_memory.active_hooks

    res_note = execute_memory_tool(
        "add_relationship_note",
        {"pair": "A-B", "note": "実は幼馴染"},
        manager,
    )
    assert res_note["success"] is True
    assert "実は幼馴染" in manager.core_memory.relationship_dynamics["A-B"]["notes"]
