# src/agents/orchestrator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, List, Optional

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
        self._active_skill_version: str = "v1"

    def register_discovered_skills(self, skill_pkg: str = "src.agents.skills.v1") -> None:
        """指定パッケージからスキルを検出し、内部レジストリに登録する。"""
        skills = SkillAgent.discover_skills(skill_pkg)
        for skill_cls in skills:
            skill_name = skill_cls.__name__.replace("Skill", "").replace("Agent", "").lower()
            self._skill_registry[skill_name] = skill_cls

    def set_skill_version(self, version: str) -> None:
        """スキルバージョンを切り替える (v1, v2 等)"""
        if version not in ("v1", "v2"):
            raise ValueError(f"Unsupported skill version: {version}")
        self._active_skill_version = version
        skill_pkg = f"src.agents.skills.{version}"
        self._skill_registry.clear()
        self.register_discovered_skills(skill_pkg)

        try:
            from src.backend.observability.metrics import record_skill_version
            for skill_name in self._skill_registry.keys():
                record_skill_version(skill_name, version)
        except Exception:
            pass

    def get_active_version(self) -> str:
        """現在アクティブなスキルバージョンを取得"""
        return self._active_skill_version

    def get_skill_class(self, skill_name: str) -> type[SkillAgent] | None:
        """登録済みスキルクラスを取得する。"""
        return self._skill_registry.get(skill_name)

    def build_execution_order(
        self, manifest: List[dict], available_skills: dict[str, type[SkillAgent]]
    ) -> List[type[SkillAgent]]:
        """マニフェストに基づき、依存関係を解決して実行順序を決定する（トポロジカルソート）。"""
        skill_nodes = {skill["name"]: skill for skill in manifest}
        from collections import defaultdict, deque

        graph = defaultdict(list)
        indegree = defaultdict(int)
        for skill in manifest:
            name = skill["name"]
            for dep in skill.get("depends_on", []):
                graph[dep].append(name)
                indegree[name] += 1
            for after in skill.get("runs_after", []):
                graph[after].append(name)
                indegree[name] += 1
            for before in skill.get("runs_before", []):
                graph[name].append(before)
                indegree[before] += 1

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

        result = []
        for name in order:
            if name in available_skills:
                result.append(available_skills[name])
            else:
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
                await self.event_bus.publish_async(
                    AgentEvent(
                        agent=current.value,
                        payload={"status": "started", "ep_num": ctx.ep_num},
                        correlation_id=self.correlation_id,
                    )
                )

            node = self.nodes.get(current)
            if node is None:
                raise RuntimeError(f"Agent node not registered: {current.value}")

            # フォールトトレラント: 個別スキル失敗を捕捉し、次のスキルへ継続可能にする
            try:
                result = await node(ctx)
                ctx.artifacts.update(result.artifacts)

                # ノード実行後イベント発行
                if self.event_bus:
                    await self.event_bus.publish_async(
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
                    # エラーが発生しても次のスキルへ継続するオプション（artifacts にエラー情報を残す）
                    ctx.artifacts[f"{current.value}_error"] = result.error
                    if self.event_bus:
                        await self.event_bus.publish_async(
                            AgentEvent(
                                agent=current.value,
                                payload={
                                    "status": "error_continued",
                                    "ep_num": ctx.ep_num,
                                    "error": result.error,
                                },
                                correlation_id=self.correlation_id,
                            )
                        )
                    current = result.next_agent
                    continue
                current = result.next_agent

            except Exception as e:
                # 予期しない例外も捕捉し、継続可能にする
                error_msg = f"Unexpected error in {current.value}: {e}"
                ctx.artifacts[f"{current.value}_exception"] = error_msg
                if self.event_bus:
                    await self.event_bus.publish_async(
                        AgentEvent(
                            agent=current.value,
                            payload={
                                "status": "exception_continued",
                                "ep_num": ctx.ep_num,
                                "error": error_msg,
                            },
                            correlation_id=self.correlation_id,
                        )
                    )
                # 次のスキルへ継続
                # エラー時の次のスキルは、ノード登録時のデフォルトを使うか、スキップする
                # ここでは単純にループを抜ける（設定で制御可能にする拡張も可能）
                raise RuntimeError(error_msg)
        return ctx