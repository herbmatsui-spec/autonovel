# src/agents/orchestrator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from src.agents.event_bus import AgentEvent, EventBus
from src.agents.skill_base import SkillAgent


class AgentName(str, Enum):
    PLANNING = "planning"
    PLOT = "plot"
    BIBLE = "bible"
    CONTEXT_BUILDER = "context_builder"
    WRITING = "writing"
    AUDIT = "audit"
    ILLUSTRATION = "illustration"
    MARKETING = "marketing"


@dataclass
class AgentContext:
    book_id: int
    branch_id: int
    ep_num: int
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    next_agent: AgentName | None
    artifacts: dict[str, Any]
    should_retry: bool = False
    error: str | None = None


AgentNode = Callable[[AgentContext], Awaitable[AgentResult]]


class Orchestrator:
    def __init__(
        self,
        nodes: dict[AgentName, AgentNode],
        event_bus: Optional[EventBus] = None,
        correlation_id: Optional[str] = None,
    ):
        self.nodes = nodes
        self.event_bus = event_bus
        self.correlation_id = correlation_id or "unknown"
        self._skill_registry: dict[str, type[SkillAgent]] = {}

    def register_discovered_skills(self, skill_pkg: str = "src.agents.skills") -> None:
        """指定パッケージからスキルを検出し、内部レジストリに登録する。"""
        skills = SkillAgent.discover_skills(skill_pkg)
        for skill_cls in skills:
            # スキル名をクラス名から生成（例: PlanningSkill -> planning）
            skill_name = skill_cls.__name__.replace("Skill", "").replace("Agent", "").lower()
            self._skill_registry[skill_name] = skill_cls

    def get_skill_class(self, skill_name: str) -> type[SkillAgent] | None:
        """登録済みスキルクラスを取得する。"""
        return self._skill_registry.get(skill_name)

    def build_execution_order(
        self, manifest: List[dict], available_skills: dict[str, type[SkillAgent]]
    ) -> List[type[SkillAgent]]:
        """マニフェストに基づき、依存関係を解決して実行順序を決定する（トポロジカルソート）。"""
        # スキル名 -> インデックスマッピング
        skill_nodes = {skill["name"]: skill for skill in manifest}
        # グラフ構築
        from collections import defaultdict, deque

        graph = defaultdict(list)
        indegree = defaultdict(int)
        for skill in manifest:
            name = skill["name"]
            for dep in skill.get("depends_on", []):
                graph[dep].append(name)
                indegree[name] += 1
            # runs_after も依存として扱う
            for after in skill.get("runs_after", []):
                graph[after].append(name)
                indegree[name] += 1
            # runs_before は逆方向の依存
            for before in skill.get("runs_before", []):
                graph[name].append(before)
                indegree[before] += 1

        # キューに indegree 0 のノードを追加
        queue = deque([name for name in skill_nodes if indegree[name] == 0])
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(skill_nodes):
            raise RuntimeError("Circular dependency detected in skill manifest")

        # 利用可能なスキルクラスにマッピング
        result = []
        for name in order:
            if name in available_skills:
                result.append(available_skills[name])
            else:
                # マニフェストにあるが未登録のスキルはスキップ（警告）
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skill '{name}' in manifest but not registered, skipping")
        return result

    def replace_skill(self, name: str, new_cls: type[SkillAgent]) -> None:
        """スキルをホットスワップで置き換える。"""
        if name in self._skill_registry:
            self._skill_registry[name] = new_cls
        else:
            raise KeyError(f"Skill '{name}' not registered")

    def get_skill_metrics(self) -> dict:
        """登録済みスキルのメトリクスを取得"""
        return SkillAgent.get_metrics()

    async def run(self, ctx: AgentContext, start: AgentName) -> AgentContext:
        current = start
        while current:
            # ノード実行前イベント発行
            if self.event_bus:
                await self.event_bus.publish(
                    AgentEvent(
                        agent=current.value,
                        payload={"status": "started", "ep_num": ctx.ep_num},
                        correlation_id=self.correlation_id,
                    )
                )

            node = self.nodes.get(current)
            if node is None:
                raise RuntimeError(f"Agent node not registered: {current.value}")

            result = await node(ctx)
            ctx.artifacts.update(result.artifacts)

            # ノード実行後イベント発行
            if self.event_bus:
                await self.event_bus.publish(
                    AgentEvent(
                        agent=current.value,
                        payload={
                            "status": "completed" if not result.error else "failed",
                            "ep_num": ctx.ep_num,
                            "next_agent": result.next_agent.value if result.next_agent else None,
                            "should_retry": result.should_retry,
                            "error": result.error,
                        },
                        correlation_id=self.correlation_id,
                    )
                )

            if result.should_retry:
                continue
            if result.error:
                raise RuntimeError(f"{current.value}: {result.error}")
            current = result.next_agent
        return ctx
