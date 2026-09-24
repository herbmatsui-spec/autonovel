"""Automatic emotional hook generator based on CoreMemory unresolved emotions."""
from __future__ import annotations

from typing import List
from src.agent.memory.core_memory import CoreMemory


def generate_hooks(core_memory: CoreMemory, plot_outline: str = "") -> List[str]:
    """CoreMemory 内の高強度感情や未解消フックから、次話で取り組むべき感情フックを生成・提案する"""
    suggested_hooks: List[str] = []

    # 1. 既存の未解決フック
    for hook in core_memory.active_hooks:
        if hook not in suggested_hooks:
            suggested_hooks.append(hook)

    # 2. 高強度感情（fear, anger, tension > 0.6 等）から対立フックを自動抽出
    for pair_key, emotions in core_memory.character_emotions.items():
        if not isinstance(emotions, dict):
            continue
        src, tgt = pair_key.split("->") if "->" in pair_key else (pair_key, "")

        fear_val = emotions.get("fear", 0.0)
        if fear_val >= 0.6:
            cause = emotions.get("cause", "")
            cause_str = f"（原因: {cause}）" if cause else ""
            suggested_hooks.append(f"{src}の{tgt}に対する恐怖({fear_val})の解消または対峙{cause_str}")

        anger_val = emotions.get("anger", 0.0)
        if anger_val >= 0.6:
            suggested_hooks.append(f"{src}の{tgt}に対する怒り({anger_val})の衝突・清算")

        tension_val = emotions.get("tension", 0.0)
        if tension_val >= 0.7:
            suggested_hooks.append(f"{src}と{tgt}の間の極度の緊張関係の緩和または決裂")

    return suggested_hooks


__all__ = ["generate_hooks"]
