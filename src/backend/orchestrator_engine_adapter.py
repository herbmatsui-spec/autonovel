"""
OrchestratorEngineAdapter - Orchestrator を旧エンジン互換インターフェースでラップするアダプター。

これにより既存のパイプラインステップが変更なしで動作する。
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.orchestrator import Orchestrator, AgentContext, AgentName
from src.agents.planning import PlanningAgent
from src.agents.writing.agent import WritingAgent as SkillWritingAgent

logger = logging.getLogger(__name__)


class PlannerAdapter:
    """PlanningAgent を旧 planner インターフェースでラップ"""

    def __init__(self, orchestrator: Orchestrator):
        self._orchestrator = orchestrator
        self._planning_agent = None

    @property
    def planning_agent(self):
        if self._planning_agent is None:
            self._planning_agent = PlanningAgent(
                repo=self._orchestrator._skill_instances.get("planning", {}).get("repo"),
                llm=self._orchestrator._skill_instances.get("planning", {}).get("llm"),
            )
        return self._planning_agent

    async def create_hegemony_plan(self, **kwargs):
        """PlanningAgent.create_hegemony_plan と互換"""
        # Orchestrator経由で planning スキルを実行
        ctx = AgentContext(
            book_id=kwargs.get("book_id", 0),
            branch_id=1,
            ep_num=1,
            artifacts=kwargs
        )
        # 実際には Orchestrator の planning ノードを直接呼び出す
        planning_node = self._orchestrator.nodes.get("planning") or self._orchestrator.nodes.get(AgentName.PLANNING)
        if planning_node:
            result = await planning_node(ctx)
            return result.artifacts.get("book_id"), result.artifacts.get("bible")
        raise NotImplementedError("Planning via Orchestrator not fully implemented")

    async def infer_easy_mode_params(self, user_prompt: str, reporter=None):
        """PlanningAgent.infer_easy_mode_params と互換"""
        # 簡易実装: PlanningAgent の同メソッドを呼び出し
        if hasattr(self.planning_agent, "infer_easy_mode_params"):
            return await self.planning_agent.infer_easy_mode_params(user_prompt, reporter=reporter)
        raise NotImplementedError


class WriterAdapter:
    """WritingAgent (Skill版) を旧 writer インターフェースでラップ"""

    def __init__(self, orchestrator: Orchestrator):
        self._orchestrator = orchestrator
        self._writing_agent = None

    @property
    def writing_agent(self):
        if self._writing_agent is None:
            writing_node = self._orchestrator.nodes.get("writing") or self._orchestrator.nodes.get(AgentName.WRITING)
            if writing_node:
                # ノードから実際の SkillWritingAgent インスタンスを取得するのは複雑なので、
                # 直接インスタンス化する
                self._writing_agent = SkillWritingAgent(
                    repo=self._orchestrator._skill_instances.get("writing", {}).get("repo"),
                    llm=self._orchestrator._skill_instances.get("writing", {}).get("llm"),
                    style_rag=self._orchestrator._skill_instances.get("writing", {}).get("style_rag"),
                    rag_prefetch=self._orchestrator._skill_instances.get("writing", {}).get("rag_prefetch"),
                )
        return self._writing_agent

    async def generate_episodes_pipeline(self, **kwargs):
        """WritingAgent.generate_episodes_pipeline と互換"""
        agent = self.writing_agent
        if agent and hasattr(agent, "generate_episodes_pipeline"):
            return await agent.generate_episodes_pipeline(**kwargs)
        raise NotImplementedError("generate_episodes_pipeline via Orchestrator not fully implemented")


class OrchestratorEngineAdapter:
    """
    Orchestrator を UltimateHegemonyEngine 互換インターフェースでラップするアダプター。

    既存のパイプラインステップ (pipeline_steps.py 等) が engine.planner, engine.writer 等を
    使用しているため、それらを Orchestrator 経由で提供する。
    """

    def __init__(self, orchestrator: Orchestrator):
        self._orchestrator = orchestrator
        self._planner = None
        self._writer = None

    @property
    def planner(self) -> PlannerAdapter:
        if self._planner is None:
            self._planner = PlannerAdapter(self._orchestrator)
        return self._planner

    @property
    def writer(self) -> WriterAdapter:
        if self._writer is None:
            self._writer = WriterAdapter(self._orchestrator)
        return self._writer

    @property
    def repo(self) -> Any:
        """リポジトリへのアクセス"""
        # 最初のスキルから repo を取得
        for skill in self._orchestrator._skill_instances.values():
            if hasattr(skill, "repo") and skill.repo:
                return skill.repo
        return None

    @property
    def llm(self) -> Any:
        for skill in self._orchestrator._skill_instances.values():
            if hasattr(skill, "llm") and skill.llm:
                return skill.llm
        return None

    @property
    def pm(self) -> Any:
        for skill in self._orchestrator._skill_instances.values():
            if hasattr(skill, "pm") and skill.pm:
                return skill.pm
        return None

    @property
    def ctx_mgr(self) -> Any:
        for skill in self._orchestrator._skill_instances.values():
            if hasattr(skill, "ctx_mgr") and skill.ctx_mgr:
                return skill.ctx_mgr
        return None

    # その他必要なプロパティを追加
    @property
    def formatter(self) -> Any:
        return None

    @property
    def validator(self) -> Any:
        return None

    @property
    def auditor(self) -> Any:
        return None

    @property
    def narrative(self) -> Any:
        return None

    @property
    def critique(self) -> Any:
        return None

    @property
    def marketing(self) -> Any:
        return None

    @property
    def bible_agent(self) -> Any:
        return None

    @property
    def plot_agent(self) -> Any:
        return None

    @property
    def style_rag(self) -> Any:
        return None

    @property
    def db(self) -> Any:
        return None

    @property
    def logic_validator(self) -> Any:
        return None

    @property
    def generate_json(self) -> Any:
        if self.llm and hasattr(self.llm, "generate_json"):
            return self.llm.generate_json
        return None

    def dispose(self) -> None:
        pass

    async def sync_bible(self, book_id: int, reporter: Any | None = None) -> Any:
        raise NotImplementedError

    async def resolve_bible_setting(self, setting_id: int, status: str) -> None:
        raise NotImplementedError

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: str | None = None,
    ) -> float:
        raise NotImplementedError

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> tuple[bool, float]:
        raise NotImplementedError