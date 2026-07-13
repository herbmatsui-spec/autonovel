import logging
from typing import Any, Dict, List

try:
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    END = None  # type: ignore
    StateGraph = None  # type: ignore
    HAS_LANGGRAPH = False

from src.backend.workflows.graph_state import WorkflowState

logger = logging.getLogger(__name__)

class PlotGraphManager:
    """
    LangGraphを用いたプロット生成オーケストレーター
    手続き的な PlotGenerationPipeline を宣言的なグラフ構造に移行
    """
    def __init__(self, engine):
        self.engine = engine
        self.repo = engine.repo
        self.pm = engine.pm
        self.ctx_mgr = engine.ctx_mgr
        self.generate_json = engine.generate_json # LLM client proxy
        self.logic_validator = engine.logic_validator
        self.auditor = engine.auditor
        self.narrative = engine.narrative

        self.workflow = self._build_graph()

    def _build_graph(self):
        if not HAS_LANGGRAPH or StateGraph is None:
            logger.warning(
                "langgraph が未インストールのため PlotGraphManager はグラフ実行をスキップします。"
            )
            return None

        workflow = StateGraph(WorkflowState)

        # ノードの追加
        workflow.add_node("align_context", self.node_align_context)
        workflow.add_node("generate_blueprint", self.node_generate_blueprint)
        workflow.add_node("audit_plot", self.node_audit_plot)
        workflow.add_node("expand_scenes", self.node_expand_scenes)
        workflow.add_node("save_plot", self.node_save_plot)

        # エッジ定義
        workflow.set_entry_point("align_context")
        workflow.add_edge("align_context", "generate_blueprint")
        workflow.add_edge("generate_blueprint", "audit_plot")

        workflow.add_conditional_edges(
            "audit_plot",
            self.should_retry_blueprint,
            {
                "retry": "generate_blueprint",
                "proceed": "expand_scenes"
            }
        )

        workflow.add_edge("expand_scenes", "save_plot")
        workflow.add_edge("save_plot", END)

        return workflow.compile()

    async def run(self, book_id: int, ep_num: int, branch_id: int = 1):
        initial_state = {
            "book_id": book_id,
            "ep_num": ep_num,
            "branch_id": branch_id,
            "retry_count": 0,
            "max_retries": 3,
            "status": "starting"
        }

        if self.workflow is None:
            # LangGraph 非依存のフォールバック: ノードを順次実行
            state: Dict[str, Any] = dict(initial_state)
            state.update(await self.node_align_context(state))
            state.update(await self.node_generate_blueprint(state))
            audit = await self.node_audit_plot(state)
            state.update(audit)
            attempts = 0
            while self.should_retry_blueprint(state) == "retry" and attempts < state.get("max_retries", 3):
                state.update(await self.node_generate_blueprint(state))
                state.update(await self.node_audit_plot(state))
                attempts += 1
            state.update(await self.node_expand_scenes(state))
            state.update(await self.node_save_plot(state))
            return state

        return await self.workflow.ainvoke(initial_state)
