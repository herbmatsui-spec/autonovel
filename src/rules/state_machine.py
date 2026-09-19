"""感情状態マシン (Week 2 Step 7)。

ペアごとの感情状態を管理する。
内部状態: Dict[(source, target, EmotionType), float]
"""
from __future__ import annotations

from typing import Dict, Iterator, Tuple

from src.pipeline.emotional_residue import EmotionType

# 感情値のクランプ範囲
MIN_VALUE = -1.0
MAX_VALUE = 1.0

StateKey = Tuple[str, str, EmotionType]


class EmotionalStateMachine:
    """ペアごとの感情状態マシン。

    source (感情を感じる側) × target (向けられる側) × emotion の組で
    感情値 (-1.0 ~ 1.0) を保持し、クランプ付き加算・減衰・スナップショットを
    提供する。
    """

    def __init__(self) -> None:
        self._state: Dict[StateKey, float] = {}
        # キーごとの減衰率 (起源ルールの decay_per_episode)
        self._decays: Dict[StateKey, float] = {}

    # ------------------------------------------------------------------
    # 基本操作
    # ------------------------------------------------------------------
    def apply_delta(
        self,
        source: str,
        target: str,
        emotion: EmotionType,
        delta: float,
        decay_per_episode: float = 0.1,
    ) -> float:
        """クランプ付き加算。新値を返却する。

        Args:
            source: 感情を感じるキャラクター名
            target: 感情を向けられるキャラクター名
            emotion: 感情タイプ
            delta: 変化量 (正負)
            decay_per_episode: このキーに紐付ける減衰率 (起源ルールの値)

        Returns:
            適用後の新値 (-1.0 ~ 1.0)
        """
        key: StateKey = (source, target, emotion)
        current = self._state.get(key, 0.0)
        new_value = max(MIN_VALUE, min(MAX_VALUE, current + float(delta)))
        self._state[key] = new_value
        self._decays[key] = max(0.0, min(1.0, float(decay_per_episode)))
        return new_value

    def set_value(
        self,
        source: str,
        target: str,
        emotion: EmotionType,
        value: float,
        decay_per_episode: float = 0.1,
    ) -> float:
        """値を直接設定 (クランプ付き)。新値を返却する。"""
        key: StateKey = (source, target, emotion)
        new_value = max(MIN_VALUE, min(MAX_VALUE, float(value)))
        self._state[key] = new_value
        self._decays[key] = max(0.0, min(1.0, float(decay_per_episode)))
        return new_value

    def get_value(self, source: str, target: str, emotion: EmotionType) -> float:
        """特定ペア・感情の値を取得 (存在しない場合は 0.0)。"""
        return self._state.get((source, target, emotion), 0.0)

    def get_state(self, source: str, target: str) -> Dict[EmotionType, float]:
        """特定ペアの全感情状態を取得。"""
        return {
            emo: val
            for (s, t, emo), val in self._state.items()
            if s == source and t == target
        }

    # ------------------------------------------------------------------
    # 減衰・スナップショット
    # ------------------------------------------------------------------
    def decay_all(self, factor: float, episodes_passed: int = 1) -> None:
        """全状態に減衰を適用する。

        キーごとに紐付いた decay_per_episode を使用し、
        ``value *= (1 - decay) ** episodes_passed`` を適用する。
        factor が指定された場合 (1 未満) は一律係数モードとして動作する。

        Args:
            factor: 一律係数モード用 (1.0 ならキーごとの decay を使用)
            episodes_passed: 経過エピソード数
        """
        clamped_factor = max(0.0, min(1.0, float(factor)))
        for key in list(self._state.keys()):
            if clamped_factor < 1.0:
                decay = clamped_factor
            else:
                decay = self._decays.get(key, 0.1)
            self._state[key] = self._state[key] * ((1.0 - decay) ** episodes_passed)

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        """シリアライズ用スナップショットを返却する。

        形式::

            {
                "A->B": {"affection": -0.6, "tension": 0.8},
                ...
            }
        """
        result: Dict[str, Dict[str, float]] = {}
        for (s, t, emo), val in self._state.items():
            pair_key = f"{s}->{t}"
            result.setdefault(pair_key, {})[emo.value] = val
        return result

    def restore(self, snapshot: Dict[str, Dict[str, float]], decays: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """スナップショットから状態を復元する。

        Args:
            snapshot: 状態スナップショット
            decays: 減衰率スナップショット (省略時はデフォルト値 0.1)
        """
        self._state.clear()
        self._decays.clear()
        default_decay = 0.1
        for pair_key, emotions in (snapshot or {}).items():
            s, _, t = pair_key.partition("->")
            pair_decays = (decays or {}).get(pair_key, {})
            for emo_str, val in (emotions or {}).items():
                try:
                    emo = EmotionType(emo_str)
                except ValueError:
                    continue
                key: StateKey = (s, t, emo)
                self._state[key] = max(MIN_VALUE, min(MAX_VALUE, float(val)))
                self._decays[key] = max(0.0, min(1.0, float(pair_decays.get(emo_str, default_decay))))

    def clear(self) -> None:
        """全状態をクリアする。"""
        self._state.clear()
        self._decays.clear()

    def decay_snapshot(self) -> Dict[str, Dict[str, float]]:
        """減衰率のスナップショットを返却する (状態スナップショットと対)。"""
        result: Dict[str, Dict[str, float]] = {}
        for (s, t, emo), decay in self._decays.items():
            pair_key = f"{s}->{t}"
            result.setdefault(pair_key, {})[emo.value] = decay
        return result

    def __len__(self) -> int:
        """保持している状態エントリ数。"""
        return len(self._state)

    def __iter__(self) -> Iterator[StateKey]:
        return iter(self._state.items())

    def items(self):
        """全 (key, value) ペアを返す。"""
        return self._state.items()


__all__ = ["EmotionalStateMachine", "MIN_VALUE", "MAX_VALUE"]
