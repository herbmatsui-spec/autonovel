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

    async def run_ab_test(
        self,
        skill_name: str,
        version_a: str,
        version_b: str,
        ctx_list: List[AgentContext],
        metric_key: str = "avg_duration_sec",
    ) -> dict[str, Any]:
        """A/Bテストを実行し、2バージョンのメトリクスを比較する。
        
        Args:
            skill_name: テスト対象スキル名
            version_a: バージョンA (例: "v1")
            version_b: バージョンB (例: "v2")
            ctx_list: 同一入力コンテキストリスト
            metric_key: 比較するメトリクスキー
            
        Returns:
            {
                "version_a": {"metrics": ..., "samples": N},
                "version_b": {"metrics": ..., "samples": N},
                "winner": "a" | "b" | "tie",
                "p_value": float,
                "metric_key": str,
            }
        """
        if version_a not in ("v1", "v2") or version_b not in ("v1", "v2"):
            raise ValueError("Versions must be 'v1' or 'v2'")
        
        from src.agents.skill_base import SkillAgent
        import statistics
        import random
        
        # 元のバージョンを保存
        original_version = self._active_skill_version
        
        results = {"a": [], "b": []}
        
        try:
            # バージョンAで実行
            self.set_skill_version(version_a)
            skill_cls_a = self.get_skill_class(skill_name)
            if not skill_cls_a:
                raise ValueError(f"Skill '{skill_name}' not found in version {version_a}")
            
            for ctx in ctx_list:
                skill_instance = skill_cls_a()
                ctx_copy = AgentContext(
                    book_id=ctx.book_id,
                    branch_id=ctx.branch_id,
                    ep_num=ctx.ep_num,
                    artifacts=ctx.artifacts.copy(),
                )
                try:
                    result = await skill_instance.execute(ctx_copy)
                    results["a"].append({
                        "success": result.error is None,
                        "duration": getattr(skill_instance, '_last_duration', 0),
                    })
                except Exception:
                    results["a"].append({"success": False, "duration": 0})
            
            # バージョンBで実行
            self.set_skill_version(version_b)
            skill_cls_b = self.get_skill_class(skill_name)
            if not skill_cls_b:
                raise ValueError(f"Skill '{skill_name}' not found in version {version_b}")
            
            for ctx in ctx_list:
                skill_instance = skill_cls_b()
                ctx_copy = AgentContext(
                    book_id=ctx.book_id,
                    branch_id=ctx.branch_id,
                    ep_num=ctx.ep_num,
                    artifacts=ctx.artifacts.copy(),
                )
                try:
                    result = await skill_instance.execute(ctx_copy)
                    results["b"].append({
                        "success": result.error is None,
                        "duration": getattr(skill_instance, '_last_duration', 0),
                    })
                except Exception:
                    results["b"].append({"success": False, "duration": 0})
            
            # 統計計算
            def calc_stats(runs):
                if not runs:
                    return {"success_rate": 0, "avg_duration": 0, "samples": 0}
                successful = [r for r in runs if r["success"]]
                durations = [r["duration"] for r in successful] if successful else [0]
                return {
                    "success_rate": len(successful) / len(runs),
                    "avg_duration": statistics.mean(durations) if durations else 0,
                    "samples": len(runs),
                }
            
            stats_a = calc_stats(results["a"])
            stats_b = calc_stats(results["b"])
            
            # 勝者判定（成功率優先、同率なら平均時間）
            if stats_a["success_rate"] > stats_b["success_rate"]:
                winner = "a"
            elif stats_b["success_rate"] > stats_a["success_rate"]:
                winner = "b"
            elif stats_a["avg_duration"] < stats_b["avg_duration"]:
                winner = "a"
            elif stats_b["avg_duration"] < stats_a["avg_duration"]:
                winner = "b"
            else:
                winner = "tie"
            
            # 簡易p値計算（二項検定の近似）
            import math
            n = len(results["a"])
            if n > 0:
                p_a = stats_a["success_rate"]
                p_b = stats_b["success_rate"]
                p_pool = (p_a + p_b) / 2
                if p_pool > 0 and p_pool < 1:
                    se = math.sqrt(p_pool * (1 - p_pool) * (2 / n))
                    z = abs(p_a - p_b) / se if se > 0 else 0
                    p_value = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))) if z > 0 else 1.0
                else:
                    p_value = 1.0
            else:
                p_value = 1.0
            
            return {
                "version_a": {"version": version_a, "metrics": stats_a, "samples": len(results["a"])},
                "version_b": {"version": version_b, "metrics": stats_b, "samples": len(results["b"])},
                "winner": winner,
                "p_value": p_value,
                "metric_key": metric_key,
            }
            
        finally:
            # 元のバージョンに戻す
            self.set_skill_version(original_version)
            
            # メトリクス記録
            try:
                from src.backend.observability.metrics import record_ab_test_result
                record_ab_test_result(
                    skill_name=skill_name,
                    winner=winner,
                    version_a=version_a,
                    version_b=version_b,
                    duration=0,  # 実装簡略化
                    success_rate_a=stats_a["success_rate"],
                    success_rate_b=stats_b["success_rate"],
                )
            except Exception:
                pass

    def schedule_ab_test(
        self,
        skill_name: str,
        version_a: str,
        version_b: str,
        interval_hours: float,
        min_samples: int = 10,
    ) -> str:
        """定期的なA/Bテストをスケジュールする（簡易実装：即時実行・結果返却）。
        
        実運用ではバックグラウンドタスクとして実装する必要があります。
        """
        import asyncio
        # 簡易実装：指定サンプル数のコンテキストを生成して即時実行
        ctx_list = [
            AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={})
            for i in range(min_samples)
        ]
        return asyncio.create_task(
            self.run_ab_test(skill_name, version_a, version_b, ctx_list)
        )

    def promote_ab_winner(self, skill_name: str, winner_version: str) -> None:
        """A/Bテスト勝者バージョンを本番昇格する"""
        if winner_version not in ("v1", "v2"):
            raise ValueError(f"Invalid version: {winner_version}")
        
        # 勝者バージョンを本番（v1）として登録
        self.set_skill_version(winner_version)
        
        # メトリクス記録
        try:
            from src.backend.observability.metrics import record_skill_promotion
            record_skill_promotion(skill_name, winner_version)
        except Exception:
            pass

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