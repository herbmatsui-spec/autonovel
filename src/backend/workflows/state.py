"""
src/backend/workflows/state.py - LangGraph ワークフロー共有状態定義 (TypedDict)

マルチエージェントオーケストレーションにおける各グラフの状態（State）のSSOT。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class BaseGraphState(TypedDict, total=False):
    """すべてのグラフで共通して利用可能な基本状態"""
    book_id: int
    branch_id: int
    status: str
    error_message: Optional[str]
    metadata: Dict[str, Any]
    step_count: int
    max_steps: int


class PlotGraphState(BaseGraphState, total=False):
    """プロット生成グラフ（PlotGraph）の状態定義"""
    genre: str
    theme: str
    target_episodes: int
    user_instructions: Optional[str]
    bible_context: Dict[str, Any]
    
    # プロット生成と推敲のループ状態
    current_iteration: int
    max_iterations: int
    num_variants: int
    plot_variants: List[Any]
    alternative_ideas: List[Dict[str, Any]]
    raw_plot_draft: str
    parsed_plots: List[Dict[str, Any]]
    critique_feedback: Optional[str]
    quality_score: float
    is_approved: bool
    suggestions: List[str]


class WritingGraphState(BaseGraphState, total=False):
    """執筆グラフ（WritingGraph）の状態定義（Actor-Criticループ）"""
    ep_num: int
    passion: float
    is_easy_mode: bool
    context: Any  # WritingContext
    prev_episode_tail: str
    sys_inst: str
    fw_prompt: str
    style_tag: Optional[str]

    # 内部イテレーション状態
    ac_iter: int
    max_ac_iter: int
    gen_ctx: Any  # WritingGenerationContext
    draft_content: str
    final_meta: Dict[str, Any]

    # 監査・評価結果
    is_integrity_ok: bool
    is_causal_ok: bool
    causal_reason: str
    failures: List[Dict[str, Any]]
    quality_score: float
    event_density: float


class ReviewGraphState(BaseGraphState, total=False):
    """推敲・レビューグラフ（ReviewGraph）の状態定義"""
    ep_num: int
    source_content: str
    
    # 各監査ノードの結果
    pacing_analysis: Dict[str, Any]
    character_consistency: Dict[str, Any]
    style_adherence: Dict[str, Any]
    
    # 総合判断と修正案
    requires_revision: bool
    revision_instructions: List[str]
    revised_content: Optional[str]
    commercial_score: float


class MasterGraphState(BaseGraphState, total=False):
    """マスターオーケストレーター（MasterGraph）の状態定義"""
    task_id: str
    mode: str  # "full_pipeline", "plot_only", "writing_batch", "review_only"
    target_start_ep: int
    target_end_ep: int
    api_call_count: int
    quality_metrics: Dict[str, Any]
    revision_budget: int
    needs_revision_eps: List[int]
    
    # 各サブグラフの実行結果
    plot_result: Optional[PlotGraphState]
    writing_results: Dict[int, WritingGraphState]
    review_results: Dict[int, ReviewGraphState]
    review_summary: Dict[str, Any]
    bible_state: Dict[str, Any]
    
    overall_progress: float
    current_phase: str
