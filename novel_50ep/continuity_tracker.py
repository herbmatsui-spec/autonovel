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
        viewpoint: str = "third_person",
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

        # 人称・視点ルールの動的生成
        self.rules.extend(self._build_persona_rules(viewpoint))

        self.prev: Optional[Union[SceneBase, Dict[str, Any]]] = None
        self.violations: List[Dict[str, Any]] = []

    def _build_persona_rules(self, viewpoint: str) -> List[Dict[str, Any]]:
        """視点に応じた一人称代名詞禁止ルールを生成"""
        if viewpoint == "third_person":
            forbidden = ["私", "僕", "俺", "あたし", "わし", "拙者",
                         "私の", "僕の", "俺の", "あたしの", "わしの", "拙者の",
                         "私が", "僕が", "俺が", "あたしが", "わしが", "拙者が",
                         "私を", "僕を", "俺を", "あたしを", "わしを", "拙者を",
                         "私に", "僕に", "俺に", "あたしに", "わしに", "拙者に"]
        elif viewpoint == "first_person_watashi":
            forbidden = ["僕", "俺", "あたし", "わし", "拙者",
                         "僕の", "俺の", "あたしの", "わしの", "拙者の",
                         "僕が", "俺が", "あたしが", "わしが", "拙者が",
                         "僕を", "俺を", "あたしを", "わしを", "拙者を",
                         "僕に", "俺に", "あたしに", "わしに", "拙者に"]
        elif viewpoint == "first_person_boku":
            forbidden = ["私", "俺", "あたし", "わし", "拙者",
                         "私の", "俺の", "あたしの", "わしの", "拙者の",
                         "私が", "俺が", "あたしが", "わしが", "拙者が",
                         "私を", "俺を", "あたしを", "わしを", "拙者を",
                         "私に", "俺に", "あたしに", "わしに", "拙者に"]
        elif viewpoint == "first_person_ore":
            forbidden = ["私", "僕", "あたし", "わし", "拙者",
                         "私の", "僕の", "あたしの", "わしの", "拙者の",
                         "私が", "僕が", "あたしが", "わしが", "拙者が",
                         "私を", "僕を", "あたしを", "わしを", "拙者を",
                         "私に", "僕に", "あたしに", "わしに", "拙者に"]
        else:
            forbidden = ["私", "僕", "俺", "あたし", "わし", "拙者"]

        return [{
            "id": "first_person_pronoun_violation",
            "type": "text",
            "op": "contains_forbidden",
            "field": "text",
            "forbidden": forbidden,
            "msg": f"視点「{viewpoint}」に合わない一人称代名詞が検出されました",
            "severity": "error",
        }]

    def feed(self, scene: Union[SceneBase, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """1シーンずつ受け取り、直前シーンとの連続性を検証 (ステップ 26, 27)"""
        v: List[Dict[str, Any]] = []
        cur_dict = scene.to_dict() if hasattr(scene, "to_dict") else scene

        # 単体チェック系ルール (contains_forbidden 等) は常に実行
        from novel_50ep.rule_engine import check_scenes
        v = check_scenes(None, cur_dict, self.rules)
        self.violations.extend(v)

        # 継続性チェック系は前シーンがある場合のみ
        if self.prev is not None:
            prev_dict = self.prev.to_dict() if hasattr(self.prev, "to_dict") else self.prev
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
