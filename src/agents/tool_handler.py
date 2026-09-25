"""Tool execution handler with error handling and dispatching."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from src.agents.memory.manager import MemoryManager
from src.agents.tools.memory_tools import execute_memory_tool

logger = logging.getLogger("agents.tool_handler")


class ToolHandler:
    """LLMからのツール呼び出し（Function Calling）をディスパッチ・実行するハンドラー"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    def handle_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """単一のツール呼び出しを実行"""
        try:
            result = execute_memory_tool(name, arguments, self.memory_manager)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name} with args {arguments}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tool": name,
            }

    def handle_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """複数のツール呼び出しを順次実行して結果リストを返却"""
        results = []
        for call in tool_calls:
            name = call.get("name") or (call.get("function", {}).get("name"))
            args = call.get("arguments") or (call.get("function", {}).get("arguments", {}))
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            res = self.handle_call(str(name), args if isinstance(args, dict) else {})
            results.append({"tool_call_id": call.get("id"), "result": res})
        return results


__all__ = ["ToolHandler"]
