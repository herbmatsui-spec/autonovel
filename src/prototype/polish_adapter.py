"""
src/prototype/polish_adapter.py - novel_50ep 用 推敲・校正アダプタ
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def polish(
    text: str,
    scene: Optional[Dict[str, Any]] = None,
    hub: Optional[Any] = None,
) -> str:
    """本番 EroticEnhancer と NarrativeState ハブの連続性指摘を適用して推敲テキストを生成する"""
    scene_ctx = scene if isinstance(scene, dict) else (scene.to_dict() if hasattr(scene, "to_dict") else {})

    # 1. 官能後処理・メタファー適用
    out = text
    try:
        from src.agents.erotic_enhancer import EroticEnhancer
        enhancer = EroticEnhancer(agent=None)
        out = enhancer.post_process_erotic_content(text, scene_ctx)
    except Exception:
        out = text

    # 2. 既存の校正フィルター（表記ゆれ・連続句読点）
    try:
        from novel_50ep.polish_tool import proofread_text
        out, _ = proofread_text(out)
    except Exception:
        pass

    # 3. ハブに連続性違反が存在する場合、修正プロンプトを付与
    if hub is not None:
        violations = getattr(hub, "continuity_violations", [])
        if violations:
            v_msgs = [f"- {v.get('field', 'continuity')}: {v.get('msg', str(v))}" for v in violations]
            rep = "\n".join(v_msgs)
            out = f"以下の矛盾を修正:\n{rep}\n\n{out}"

    return out
