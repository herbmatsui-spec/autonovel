from typing import Dict

from pydantic import BaseModel, Field


class InteractionConfig(BaseModel):
    """
    カーネル間の相互作用係数を定義する設定モデル。
    matrix[target][source] = coefficient
    """
    # 相互作用行列: target_kernel -> {source_kernel: coefficient}
    # 例: "resonance": {"hegemony": -0.2} は、覇権が共鳴を抑制することを意味する
    matrix: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "resonance": {"resonance": 0.05, "hegemony": -0.2, "conflict": -0.1, "serenity": 0.2},
            "hegemony": {"resonance": -0.1, "hegemony": 0.05, "conflict": 0.1, "serenity": -0.1},
            "conflict": {"resonance": -0.1, "hegemony": 0.2, "conflict": 0.05, "serenity": -0.2},
            "serenity": {"resonance": 0.1, "hegemony": -0.2, "conflict": -0.3, "serenity": 0.05},
        }
    )

    # 時間経過による状態の減衰率 (1.0 = 減衰なし)
    decay_rate: float = 0.98

    # 状態のクランプ範囲
    min_value: float = 0.0
    max_value: float = 100.0

