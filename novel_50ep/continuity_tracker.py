"""インクリメンタル連続性トラッカー (Phase 3 / ステップ 25〜30)"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Union
from novel_50ep.rule_engine import load_rules, check_scenes
from novel_50ep.scene_model import SceneBase


class ContinuityTracker:
    """シーン間連続性トラッカー (ステップ 25〜30, 58)"""

    def __init__(
        self,
        rules_dir: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        expects: Optional[List[Dict[str, Any]]] = None,
    ):
        self.rules: List[Dict[str, Any]] = []
        if rules_dir and os.path.exists(rules_dir):
            self.rules.extend(load_rules(rules_dir))
        if rules:
            self.rules.extend(rules)

        # ステップ 58: 伏線ルールの取り込み対応
        if expects:
            from novel_50ep.rule_engine import build_foreshadow_rules
            self.rules.extend(build_foreshadow_rules(expects))

        self.prev: Optional[Union[SceneBase, Dict[str, Any]]] = None
        self.violations: List[Dict[str, Any]] = []

    def feed(self, scene: Union[SceneBase, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """1シーンずつ受け取り、直前シーンとの連続性を検証 (ステップ 26, 27)"""
        v: List[Dict[str, Any]] = []
        if self.prev is not None and scene is not None:
            prev_dict = self.prev.to_dict() if hasattr(self.prev, "to_dict") else self.prev
            cur_dict = scene.to_dict() if hasattr(scene, "to_dict") else scene
            v = check_scenes(prev_dict, cur_dict, self.rules)
            self.violations.extend(v)

        self.prev = scene
        return v

    def reset(self) -> None:
        """状態を初期化 (ステップ 28)"""
        self.prev = None
        self.violations = []

    def save(self, path: str) -> None:
        """違反履歴を JSON に保存 (ステップ 29)"""
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, mode="w", encoding="utf-8") as fp:
            json.dump(self.violations, fp, ensure_ascii=False, indent=2)

    def report(self) -> str:
        """人間可読な違反レポート文字列を生成 (ステップ 30)"""
        if not self.violations:
            return ""
        return "\n".join(f"{v['field']}: {v['msg']}" for v in self.violations)
