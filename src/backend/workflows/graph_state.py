from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    """グラフ全体で共有される状態"""
    book_id: int
    ep_num: int
    branch_id: int
    # コンテキスト
    context_alignment: Dict[str, Any] = Field(default_factory=dict)
    blueprint: Dict[str, Any] = Field(default_factory=dict)
    final_plot: Dict[str, Any] = Field(default_factory=dict)
    # 監査結果
    audit_results: List[Dict[str, Any]] = Field(default_factory=list)
    is_consistent: bool = Field(default=True)
    # 制御フラグ
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    status: str = Field(default="pending") # 'success', 'failed', 'needs_retry'

class PlotNodeOutput(BaseModel):
    """ノード間のデータ受け渡し用モデル"""
    status: str
    data: Dict[str, Any]
    error: Optional[str] = None
