# src/agents/audit_agent.py
from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.agents.audit import (
    LogicalAuditor,
    DeAIAuditor,
    FastPlotScreener,
    AbilityConsistencyChecker,
    PlotIntegrityMonitor,
)
from src.models.audit import CriticFeedback, LogicalAuditIssueList
from src.models.sharp_edge import SharpEdgeSpec


class AuditAgent(BaseAgent):
    """品質監査を担当するエージェント（ファサード）。
    既存の複数の監査クラスを統合し、統一インターフェースを提供する。
    """

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        prompt_manager: Any = None,
        edge_preserver: Any = None,
        **kwargs,
    ):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

        # 内部監査コンポーネントを初期化
        self._logical_auditor = LogicalAuditor(
            repo=repo, llm=llm, pm=prompt_manager, generate_json=llm
        )
        self._deai_auditor = DeAIAuditor(
            repo=repo, llm=llm, prompt_manager=prompt_manager, edge_preserver=edge_preserver
        )
        self._fast_screener = FastPlotScreener(llm=llm, prompt_manager=prompt_manager)
        self._ability_checker = AbilityConsistencyChecker(llm=llm, prompt_manager=prompt_manager)
        self._plot_monitor = PlotIntegrityMonitor()

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。
        書かれた本文を監査し、合格なら次へ、不合格なら WritingAgent に戻す。
        """
        writing_context = ctx.artifacts.get("writing_context")
        drafted_text = ctx.artifacts.get("drafted_text")

        if not writing_context or not drafted_text:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="writing_context and drafted_text are required in artifacts",
            )

        book_id = ctx.book_id
        ep_num = ctx.ep_num

        try:
            # 1. プロット高速スクリーニング
            blueprint = writing_context.get("plot", {}).get("detailed_blueprint", "")
            if blueprint:
                is_valid, feedback = await self._fast_screener.screen_plot(blueprint)
                if not is_valid:
                    return AgentResult(
                        next_agent=AgentName.WRITING,
                        should_retry=True,
                        artifacts={"audit_feedback": f"Fast screen failed: {feedback}"},
                    )

            # 2. 論理整合性監査
            logical_ok, logical_feedback, _ = await self._logical_auditor.audit_logical_consistency(
                book_id=book_id, ep_num=ep_num, blueprint=blueprint
            )
            if not logical_ok:
                return AgentResult(
                    next_agent=AgentName.WRITING,
                    should_retry=True,
                    artifacts={"audit_feedback": f"Logical audit failed: {logical_feedback}"},
                )

            # 3. AI感除去監査（DeAI）
            edges = writing_context.get("sharp_edges", [])
            emotional_hook = writing_context.get("emotional_hook")
            deai_ok, deai_feedback = await self._deai_auditor.audit(
                content=drafted_text,
                before_content=writing_context.get("prev_ctx", ""),
                edges=edges,
                emotional_hook=emotional_hook,
            )
            if not deai_ok:
                return AgentResult(
                    next_agent=AgentName.WRITING,
                    should_retry=True,
                    artifacts={"audit_feedback": f"DeAI audit failed: {deai_feedback}"},
                )

            # 4. 能力整合性チェック
            settings_json = writing_context.get("world_settings", "{}")
            chars_json = writing_context.get("characters_json", "[]")
            ability_ok, ability_feedback, _ = await self._ability_checker.audit_ability_consistency(
                blueprint=drafted_text, settings_json=settings_json, characters_json=chars_json
            )
            if not ability_ok:
                return AgentResult(
                    next_agent=AgentName.WRITING,
                    should_retry=True,
                    artifacts={"audit_feedback": f"Ability consistency failed: {ability_feedback}"},
                )

            # 5. プロット整合性モニター（因果律）
            keywords = self._plot_monitor.extract_keywords(drafted_text)
            causal_ok, score, failures = await self._plot_monitor.check_integrity(
                keywords=keywords,
                blueprint=blueprint,
                content=drafted_text,
                threshold=0.7,
            )
            if not causal_ok:
                return AgentResult(
                    next_agent=AgentName.WRITING,
                    should_retry=True,
                    artifacts={"audit_feedback": f"Causal integrity failed: {failures}"},
                )

            # 全監査合格
            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "audit_report": {
                        "logical": "passed",
                        "deai": "passed",
                        "ability": "passed",
                        "causal": "passed",
                    }
                },
            )

        except Exception as e:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Audit failed with exception: {e}",
            )