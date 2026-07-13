from typing import Dict

import yaml

from kernels.base import KernelContext, KernelState
from kernels.interaction_config import InteractionConfig


class InteractionManager:
    """
    カーネル間相互作用行列 (KIM) を管理し、状態ベクトルを更新するマネージャー。
    """
    def __init__(self, config_path: str = "config/interaction_matrix.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> InteractionConfig:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        # yaml構造をInteractionConfigの形式に変換
        matrix = {}
        for target, sources in data.items():
            if isinstance(sources, dict):
                matrix[target] = sources

        return InteractionConfig(
            matrix=matrix,
            decay_rate=data.get('decay_rate', 0.98),
            min_value=data.get('min_value', 0.0),
            max_value=data.get('max_value', 100.0)
        )

    async def compute_next_state(self, current_state: KernelState, external_impact: Dict[str, float], context: KernelContext) -> KernelState:
        """
        相互作用行列を用いて次の状態を計算する。
        S_{t+1} = clamp(S_t * decay + M * S_t + I, min, max)
        """
        # 現在の値を辞書形式で取得
        s_t = current_state.dict()
        new_values = {}

        for target, sources in self.config.matrix.items():
            # 1. 基本的な減衰
            val = s_t.get(target, 0.0) * self.config.decay_rate

            # 2. 相互作用の加算 (M * S_t)
            interaction_sum = 0.0
            for source, coefficient in sources.items():
                interaction_sum += s_t.get(source, 0.0) * coefficient

            # 3. 外部刺激の加算 (I)
            impact = external_impact.get(target, 0.0)

            # 合計
            val += interaction_sum + impact

            # 4. クランプ処理
            new_values[target] = max(self.config.min_value, min(self.config.max_value, val))

        return KernelState(**new_values)

    def get_interaction_description(self, state: KernelState) -> str:
        """
        現在の状態ベクトルを人間が理解しやすい形式の記述に変換する（プロンプト用）。
        """
        descriptions = []
        if state.hegemony > 70: descriptions.append("強力な覇権的支配が場を支配している")
        if state.resonance > 70: descriptions.append("深い魂の共鳴が起きている")
        if state.conflict > 70: descriptions.append("激しい葛藤が衝突している")
        if state.serenity > 70: descriptions.append("静謐な空気が流れている")

        return " / ".join(descriptions) if descriptions else "安定した均衡状態にある"

