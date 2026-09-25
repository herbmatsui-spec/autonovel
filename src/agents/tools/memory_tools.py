"""Function calling tools and schema definitions for agent memory operations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.agents.memory.manager import MemoryManager

# OpenAI / Anthropic 互換のツールスキーマ定義
MEMORY_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "update_emotion",
            "description": "キャラクター間の感情値を更新（デルタ加算）する",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "感情の主体キャラ名"},
                    "target": {"type": "string", "description": "感情の対象キャラ名"},
                    "emotion": {"type": "string", "description": "感情種別 (fear, affection, tension, etc.)"},
                    "delta": {"type": "number", "description": "変化量 (-1.0 ~ 1.0)"},
                    "reason": {"type": "string", "description": "感情変化の理由・原因"},
                },
                "required": ["source", "target", "emotion", "delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_emotional_context",
            "description": "指定キャラペアの現在の感情状態を取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "主体キャラ名"},
                    "target": {"type": "string", "description": "対象キャラ名"},
                },
                "required": ["source", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_similar_scene",
            "description": "過去エピソードから類似の感情シーンや要約を想起・検索する",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ"},
                    "k": {"type": "integer", "description": "取得件数", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trace_emotional_cause",
            "description": "特定の感情の因果関係（原因となった過去イベント）を追跡する",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "主体キャラ名"},
                    "target": {"type": "string", "description": "対象キャラ名"},
                    "emotion": {"type": "string", "description": "感情種別"},
                },
                "required": ["source", "target", "emotion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_relationship_note",
            "description": "ペア間の関係性に関するメモや特記事項を追加する",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "ペア名 ('A-B')"},
                    "note": {"type": "string", "description": "メモ内容"},
                },
                "required": ["pair", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compact_core_memory",
            "description": "CoreMemory のトークン圧縮を実行する",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_active_hook",
            "description": "今話で解決すべき感情フック・対立課題をセットする",
            "parameters": {
                "type": "object",
                "properties": {
                    "hook": {"type": "string", "description": "フック内容"},
                },
                "required": ["hook"],
            },
        },
    },
]


def execute_memory_tool(
    name: str,
    args: Dict[str, Any],
    manager: MemoryManager,
) -> Dict[str, Any]:
    """ツール名と引数を受け取り、MemoryManager で実行した結果を返却する"""
    if name == "update_emotion":
        source = args["source"]
        target = args["target"]
        emotion = args["emotion"]
        delta = float(args["delta"])
        reason = args.get("reason", "")
        new_val = manager.update_emotion(source, target, emotion, delta, reason=reason)
        return {
            "success": True,
            "source": source,
            "target": target,
            "emotion": emotion,
            "new_value": new_val,
        }

    elif name == "get_emotional_context":
        pair = (args["source"], args["target"])
        ctx = manager.get_emotional_context(pair)
        return {"success": True, "context": ctx}

    elif name == "recall_similar_scene":
        query = args["query"]
        k = int(args.get("k", 3))
        entries = manager.recall_similar(query, k=k)
        return {
            "success": True,
            "results": [e.to_dict() for e in entries],
        }

    elif name == "trace_emotional_cause":
        causes = manager.trace_cause(args["source"], args["target"], args["emotion"])
        return {"success": True, "causes": causes}

    elif name == "add_relationship_note":
        pair = args["pair"]
        note = args["note"]
        dyn = manager.core_memory.relationship_dynamics.setdefault(pair, {})
        notes = dyn.setdefault("notes", [])
        notes.append(note)
        return {"success": True, "pair": pair, "notes_count": len(notes)}

    elif name == "compact_core_memory":
        compacted = manager.compact()
        return {"success": True, "compacted": compacted}

    elif name == "set_active_hook":
        hook = args["hook"]
        manager.core_memory.active_hooks.append(hook)
        return {"success": True, "active_hooks": manager.core_memory.active_hooks}

    else:
        return {"success": False, "error": f"Unknown memory tool: {name}"}


__all__ = ["MEMORY_TOOLS_SCHEMA", "execute_memory_tool"]
