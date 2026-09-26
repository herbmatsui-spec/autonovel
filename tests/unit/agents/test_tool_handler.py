"""Unit tests for ToolHandler."""
from src.agents.memory.manager import MemoryManager
from src.agents.tool_handler import ToolHandler


def test_tool_error_handling():
    manager = MemoryManager()
    handler = ToolHandler(manager)

    # 正常実行
    res = handler.handle_call("update_emotion", {"source": "A", "target": "B", "emotion": "fear", "delta": 0.5})
    assert res["success"] is True

    # 引数不足エラー
    res_err = handler.handle_call("update_emotion", {"source": "A"})
    assert res_err["success"] is False
    assert "error" in res_err

    # 未知ツールエラー
    res_unknown = handler.handle_call("non_existent_tool", {})
    assert res_unknown["success"] is False
