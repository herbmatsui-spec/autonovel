from enum import Enum
from typing import Dict, List, Tuple


class WorkflowType(str, Enum):
    """バックグラウンドワークフローの種別を定義する列挙型"""
    FULL_AUTO = "full_auto_workflow"
    EPISODE_WRITING = "episode_writing_workflow"
    PLOT_EXPANSION = "plot_expansion_workflow"
    PLOT_REBUILD = "plot_rebuild_workflow"
    CRITIQUE_OPTIMIZE = "run_critique_optimization_workflow"
    PLAN_GENERATION = "plan_generation_workflow"
    RETRY_FAILED = "retry_failed_episodes_workflow"
    IMPORT_CHAPTER = "chapter_import_workflow"
    MARKETING_GENERATION = "marketing_generation_workflow"
    EROTIC_REFINEMENT = "erotic_refinement_workflow"

# WorkflowType → (api_client関数名, 必要な引数名リスト)
WORKFLOW_API_MAP: Dict[WorkflowType, Tuple[str, List[str]]] = {
    WorkflowType.FULL_AUTO: (
        "generate_easy",
        ["genre", "keywords", "archetype_key", "target_eps", "initial_limit", "word_count", "concept", "tone_vibe"]
    ),
    WorkflowType.EPISODE_WRITING: (
        "generate_episodes",
        ["book_id", "write_from", "write_to", "passion", "word_count", "do_refine", "env_state", "pipeline_mode"]
    ),
    WorkflowType.PLOT_EXPANSION: (
        "expand_plots",
        ["book_id", "gen_from", "gen_to"]
    ),
    WorkflowType.PLOT_REBUILD: (
        "rebuild_plots",
        ["params"]
    ),
    WorkflowType.CRITIQUE_OPTIMIZE: (
        "critique_optimize",
        ["book_id"]
    ),
    WorkflowType.PLAN_GENERATION: (
        "plan_generation",
        ["params"]
    ),
    WorkflowType.RETRY_FAILED: (
        "retry_failed_episodes",
        ["book_id", "passion", "word_count"]
    ),
    WorkflowType.IMPORT_CHAPTER: (
        "import_chapter",
        ["book_id", "ep_num", "import_text", "do_refine"]
    ),
    WorkflowType.MARKETING_GENERATION: (
        "generate_marketing",
        ["book_id", "latest_ep"]
    ),
    WorkflowType.EROTIC_REFINEMENT: (
        "refine_erotic",
        ["book_id", "ep_num", "intensity", "platform_preset"]
    ),
}
