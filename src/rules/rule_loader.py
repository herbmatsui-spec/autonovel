"""ルールローダー (Week 2 Step 4)。

YAML ルールセットファイルをロードし、EmotionalRule のリストを生成する。
条件関数は文字列式を eval せず、conditions モジュールのレジストリから参照する。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.pipeline.emotional_residue import EmotionType
from src.rules.conditions import condition_registry
from src.rules.emotional_rules import EmotionalRule
from src.rules.plot_events import PlotEvent, PlotEventType, Role

logger = logging.getLogger(__name__)

# デフォルトのルールセットパス (リポジトリルート相関)
DEFAULT_RULES_PATH = str(Path(__file__).resolve().parents[2] / "config" / "emotional_rules.yaml")
DEFAULT_EVENTS_PATH = str(Path(__file__).resolve().parents[2] / "config" / "plot_events.yaml")


class RuleLoader:
    """感情変化ルールのローダー。"""

    def load_rules(self, path: str = DEFAULT_RULES_PATH) -> List[EmotionalRule]:
        """YAML からルールリストをロードする。

        Args:
            path: ルールセット YAML のパス

        Returns:
            EmotionalRule のリスト (不正なルールはスキップ)

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: YAML 構造が不正な場合
        """
        rule_path = Path(path)
        if not rule_path.exists():
            raise FileNotFoundError(f"Rules file not found: {path}")

        with rule_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "rules" not in data:
            raise ValueError(f"Invalid rules file structure: {path}")

        rules: List[EmotionalRule] = []
        for idx, raw in enumerate(data["rules"] or []):
            rule = self._build_rule(raw, idx)
            if rule is not None:
                rules.append(rule)
        logger.info("Loaded %d emotional rules from %s", len(rules), path)
        return rules

    def _build_rule(self, raw: Optional[Dict[str, Any]], idx: int) -> Optional[EmotionalRule]:
        """辞書 1件から EmotionalRule を生成 (不正時は None)。"""
        if not isinstance(raw, dict):
            logger.warning("Rule #%d is not a mapping; skipped", idx)
            return None
        try:
            event_type = PlotEventType(str(raw["event_type"]).lower())
            source_role = Role(str(raw["source_role"]).lower())
            target_role = Role(str(raw["target_role"]).lower())
            deltas_raw = raw.get("emotion_deltas") or {}
            deltas = {EmotionType(str(k).lower()): float(v) for k, v in deltas_raw.items()}
        except (KeyError, ValueError) as e:
            logger.warning("Rule #%d invalid (%s); skipped", idx, e)
            return None

        # 条件関数はレジストリから参照 (eval 不使用)
        condition = None
        condition_name = raw.get("condition")
        if condition_name:
            name = str(condition_name).strip()
            if condition_registry.has(name):
                params = raw.get("condition_params") or {}
                condition = condition_registry.create(name, **params)
            else:
                logger.warning(
                    "Rule #%d references unknown condition %r; applying unconditionally",
                    idx, name,
                )

        return EmotionalRule(
            event_type=event_type,
            source_role=source_role,
            target_role=target_role,
            emotion_deltas=deltas,
            condition=condition,
            decay_per_episode=float(raw.get("decay_per_episode", 0.1)),
            rule_id=str(raw.get("rule_id", f"rule_{idx}")),
        )


def parse_episode_events(path: str = DEFAULT_EVENTS_PATH) -> Dict[int, List[PlotEvent]]:
    """プロットイベント YAML をパースしてエピソード別のイベントリストを返す。

    YAML 構造::

        episode_14:
          - event_id: "ep14_betrayal"
            event_type: "betrayal"
            scene: 3
            roles: {victim: "A", perpetrator: "B"}

    Args:
        path: プロットイベント YAML のパス

    Returns:
        エピソード番号 → PlotEvent リストの辞書
    """
    events_path = Path(path)
    if not events_path.exists():
        raise FileNotFoundError(f"Plot events file not found: {path}")

    with events_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    result: Dict[int, List[PlotEvent]] = {}
    for key, events in data.items():
        ep = _extract_episode_number(str(key))
        if ep is None:
            logger.warning("Skipping unrecognized episode key: %s", key)
            continue
        parsed: List[PlotEvent] = []
        for raw in events or []:
            try:
                event = PlotEvent.from_dict({**raw, "episode": ep})
                parsed.append(event)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Invalid event in %s: %s; skipped", key, e)
        result[ep] = parsed
    return result


def _extract_episode_number(key: str) -> Optional[int]:
    """"episode_14" 形式のキーから番号を抽出。"""
    lowered = key.strip().lower()
    if lowered.startswith("episode_"):
        try:
            return int(lowered.split("_", 1)[1])
        except ValueError:
            return None
    return None


__all__ = ["RuleLoader", "parse_episode_events", "DEFAULT_RULES_PATH", "DEFAULT_EVENTS_PATH"]
