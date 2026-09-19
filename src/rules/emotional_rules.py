"""感情変化ルール定義 (Week 2 Step 2)。

プロットイベントに対する感情変化のルールと、ルール評価用コンテキスト。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from src.pipeline.emotional_residue import EmotionType
from src.rules.plot_events import PlotEvent, PlotEventType, Role


@dataclass
class PlotContext:
    """ルール評価用コンテキスト。

    Attributes:
        episode: 現在のエピソード番号
        event: 評価対象のプロットイベント
        roles: 役割 → キャラクター名 (event から展開済み)
        relationship_level: 関係レベル (0.0 ~ 1.0、既存の関係性データから算出)
        previous_tension: 直前の緊張度
        custom_data: カスタムフラグ等の任意データ
    """

    episode: int
    event: Optional[PlotEvent] = None
    roles: Dict[Role, str] = field(default_factory=dict)
    relationship_level: float = 0.0
    previous_tension: float = 0.0
    custom_data: Dict[str, Any] = field(default_factory=dict)


def _default_condition(ctx: PlotContext) -> bool:
    """デフォルト条件: 常に真。"""
    return True


@dataclass
class EmotionalRule:
    """感情変化ルール。

    プロットイベント (event_type) が発生したとき、source_role のキャラクターが
    target_role のキャラクターに対して emotion_deltas 分の感情変化を経験する。

    Attributes:
        event_type: 対象イベントタイプ
        source_role: 感情を感じる側の役割
        target_role: 感情を向けられる側の役割
        emotion_deltas: 感情タイプ → 変化量のマッピング
        condition: 適用条件関数 (PlotContext を受け取り bool を返す)
        decay_per_episode: 1話あたりの減衰率 (0.0 ~ 1.0)
        rule_id: ルールの識別子 (デバッグ用、任意)
    """

    event_type: PlotEventType
    source_role: Role
    target_role: Role
    emotion_deltas: Dict[EmotionType, float]
    condition: Callable[[PlotContext], bool] = field(default=_default_condition)
    decay_per_episode: float = 0.1
    rule_id: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.event_type, str):
            self.event_type = PlotEventType(self.event_type)
        if isinstance(self.source_role, str):
            self.source_role = Role(self.source_role)
        if isinstance(self.target_role, str):
            self.target_role = Role(self.target_role)
        # 文字列キーの EmotionType を正規化
        normalized: Dict[EmotionType, float] = {}
        for key, val in self.emotion_deltas.items():
            if isinstance(key, str):
                normalized[EmotionType(key)] = float(val)
            else:
                normalized[key] = float(val)
        self.emotion_deltas = normalized

    def matches(self, event: PlotEvent) -> bool:
        """イベントタイプが一致するか判定。"""
        return self.event_type == event.event_type

    def evaluate(self, ctx: PlotContext) -> bool:
        """条件関数を評価。条件関数実行時の例外は False 扱いとする。

        条件関数が未設定 (None) の場合は常に適用 (True) とする。
        """
        if self.condition is None:
            return True
        try:
            return bool(self.condition(ctx))
        except Exception:
            return False


__all__ = ["EmotionalRule", "PlotContext"]
