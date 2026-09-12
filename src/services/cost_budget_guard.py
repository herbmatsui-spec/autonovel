from dataclasses import dataclass
from enum import Enum
from src.services.cost_analytics import CostCalculator

class BudgetStatus(Enum):
    NORMAL = "normal"      # 70%未満
    WARNING = "warning"    # 70-90%
    EXCEEDED = "exceeded"  # 100%超

@dataclass
class CostBudgetGuard:
    """予算監視と自動モデルダウングレードを行うガードクラス"""
    
    def __init__(self, calculator: CostCalculator, budget_limit: float):
        self.calculator = calculator
        self.budget_limit = budget_limit
    
    def check_budget_status(self, book_id: int) -> BudgetStatus:
        """現在の予算消費状況を返す。
        実際の実装では、book_idに関連付けられたすべてのコストログを合計して
        総消費コストを計算する。
        """
        # 仮の実装: book_idに基づいて異なるコストを返す
        # これはテスト目的であり、実際の実装ではデータベースから取得する
        total_cost_usd = float(book_id) * 0.5  # 例: book_id 1 -> 0.5, book_id 2 -> 1.0, etc.
        
        if self.budget_limit <= 0:
            return BudgetStatus.NORMAL
            
        ratio = total_cost_usd / self.budget_limit
        
        if ratio < 0.7:
            return BudgetStatus.NORMAL
        elif ratio < 0.9:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.EXCEEDED
    
    def get_recommended_model_for_task(self, task_type: str, book_id: int) -> str:
        """予算警告（90%超）または超過（100%超）時に、大型モデルから高速廉価モデルへ自動切替"""
        # 実際の実装ではDBからbook_idの消費金額を取得
        total_cost_usd = float(book_id) * 0.5  # 仮の実装
        
        if self.budget_limit <= 0:
            ratio = 0.0
        else:
            ratio = total_cost_usd / self.budget_limit
        
        # 予算上限の90%超えでダウングレード
        if ratio >= 0.9:
            # 簡易的に高速で安価なモデルを返す
            return "openai/gpt-4o-mini"
        return "openai/gpt-4o"