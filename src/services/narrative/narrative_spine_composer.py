"""
narrative_spine_composer.py - EmotionalHookSpec と SharpEdgeSpec をプロンプトに統合するコンポーザー
"""
from __future__ import annotations

from typing import Optional

from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec


class NarrativeSpineComposer:
    def __init__(
        self,
        hook_spec: Optional[EmotionalHookSpec] = None,
        edge_spec: Optional[SharpEdgeSpec] = None,
    ) -> None:
        self.hook_spec = hook_spec
        self.edge_spec = edge_spec

    def compose_constraints(self) -> str:
        parts = ["【🚨商業ナラティブ軸制約（絶対遵守）】"]
        if self.hook_spec:
            parts.append(
                f"- 感情起点 (Emotional Hook): 「{self.hook_spec.hook_name}」\n"
                f"  意図: {self.hook_spec.one_line_intent}\n"
                f"  目標テンションピーク: {self.hook_spec.target_tension_peak} (品質はこの感情に従属します)"
            )
        if self.edge_spec:
            parts.append(
                f"- 削ってはいけない角 (Sharp Edge): [{self.edge_spec.edge_type}] {self.edge_spec.description}\n"
                f"  キーフレーズ（保全対象）: 「{self.edge_spec.key_phrase}」"
            )
        if len(parts) == 1:
            return ""
        return "\n".join(parts)
