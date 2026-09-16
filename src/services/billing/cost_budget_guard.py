"""トークン消費上限 (Cost Budget Guard) モデル。"""
from dataclasses import dataclass


@dataclass
class CostBudgetConfig:
    max_tokens_per_episode: int = 40_000      # 1話あたりの最大消費トークン
    max_cost_yen_per_episode: float = 15.0    # 1話あたりの最大円換算コスト
    max_pdca_iterations: int = 3              # 最大書き直し反復回数
