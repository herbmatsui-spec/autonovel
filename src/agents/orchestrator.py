# src/agents/orchestrator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional

from src.agents.event_bus import AgentEvent, EventBus
from src.agents.skill_base import SkillAgent

if TYPE_CHECKING:
    from src.backend.tasks.dag_models import DAGGraph
    from src.backend.tasks.dag_scheduler import DAGScheduler


class CyclicDependencyError(ValueError):
    """スキル間の循環依存が検出された場合に送出されるエラー"""
    pass


class AgentName(str, Enum):
    PLANNING = "planning"
    PLOT = "plot"
    BIBLE = "bible"
    CONTEXT_BUILDER = "context_builder"
    WRITING = "writing"
    ENRICHMENT = "enrichment"
    AUDIT = "audit"
    ILLUSTRATION = "illustration"
    MARKETING = "marketing"


@dataclass
class AgentContext:
    book_id: int
    branch_id: int
    ep_num: int
    artifacts: dict[str, Any] = field(default_factory=dict)
    backtrack_history: list[dict] = field(default_factory=list)


@dataclass
class AgentResult:
    next_agent: AgentName | str | None
    artifacts: dict[str, Any]
    should_retry: bool = False
    error: str | None = None
    is_backtrack: bool = False


AgentNode = Callable[[AgentContext], Awaitable[AgentResult]]


def _make_skill_node(inst: SkillAgent, nxt: str | None) -> AgentNode:
    """トポロジカル順序の次ノードを自動設定するノードクロージャ"""
    async def _node(ctx: AgentContext) -> AgentResult:
        res = await inst.run(ctx)
        if res.next_agent is None and nxt is not None and not res.error:
            res.next_agent = nxt
        return res
    return _node


class Orchestrator:
    def __init__(
        self,
        nodes: dict[AgentName | str, AgentNode],
        event_bus: Optional[EventBus] = None,
        correlation_id: Optional[str] = None,
        max_backtracks_per_node: int = 3,
        dag_scheduler: "DAGScheduler | None" = None,
        use_dag_scheduler: bool = False,
    ):
        self.nodes = nodes
        self.event_bus = event_bus
        self.correlation_id = correlation_id or "unknown"
        self.max_backtracks_per_node = max_backtracks_per_node
        self.dag_scheduler = dag_scheduler
        self.use_dag_scheduler = use_dag_scheduler
        self._skill_registry: dict[str, type[SkillAgent]] = {}
        self._active_skill_version: str = "v1"
        self._ordered_skill_names: list[str] = []
        self._skill_instances: dict[str, SkillAgent] = {}
        

    def _build_dag_graph(self) -> "DAGGraph":
        """Orchestrator のスキル順序に基づいて DAGGraph を構築する"""
        from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskResourceRequirement
        
        graph = DAGGraph(dag_id=f"orch_{self.correlation_id}")
        
        # 各スキルを DAGTaskNode に変換
        for i, skill_name in enumerate(self._ordered_skill_names):
            task_id = f"{self.correlation_id}_{skill_name}"
            
            # 依存関係：最初のスキル以外は前のスキルに依存
            if i == 0:
                dependencies = []
                kwargs = {
                    "task_id": task_id,
                    # 最初のタスクには入力元がない
                }
            else:
                prev_skill_name = self._ordered_skill_names[i-1]
                prev_task_id = f"{self.correlation_id}_{prev_skill_name}"
                dependencies = [prev_task_id]
                kwargs = {
                    "task_id": task_id,
                    "input_from": prev_task_id,  # 前のタスクからデータを取得する
                }
            
            # デフォルトのリソース要件（後で設定可能にする）
            resources = TaskResourceRequirement(
                cpu_cores=1.0,
                ram_mb=512,
                gpu_mem_mb=0
            )
            
            # DAGTaskNode を作成
            task_node = DAGTaskNode(
                task_id=task_id,
                name=skill_name,  # 人間が読めるラベル
                func_name=skill_name,  # 登録された関数名と一致させる
                kwargs=kwargs,  # タスク実行時に渡される引数
                dependencies=dependencies,
                resources=resources,
                priority=10 - i,  # 番号が若いほど高優先度（実行順序と同じ)
                timeout_seconds=300.0,  # 5分のデフォルトタイムアウト
                retry_limit=3,
            )
            
            graph.add_node(task_node)
        
        return graph

    def _register_skills_to_scheduler(self) -> None:
        """スキルの実行関数を DAGScheduler のタスクレジストリに登録する"""
        if not self.dag_scheduler or not self._skill_instances:
            return
        
        # スキルインスタンスから run メソッドを取得して登録
        for skill_name, skill_instance in self._skill_instances.items():
            self.dag_scheduler.register_task(skill_name, skill_instance.run)


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
        self, manifest: List[dict] | Any, available_skills: dict[str, type[SkillAgent]] | None = None
    ) -> List[type[SkillAgent]]:
        """マニフェストに基づき、依存関係を解決して実行順序を決定する（トポロジカルソート）。"""
        from collections import defaultdict, deque

        raw_list = manifest.skills if hasattr(manifest, "skills") else manifest
        skills_data = []
        for s in raw_list:
            if hasattr(s, "model_dump"):
                skills_data.append(s.model_dump(by_alias=True))
            elif isinstance(s, dict):
                skills_data.append(s)

        skill_nodes = {s["name"]: s for s in skills_data}
        graph = defaultdict(list)
        indegree = defaultdict(int)
        for skill in skills_data:
            name = skill["name"]
            for dep in skill.get("depends_on", []):
                if dep in skill_nodes:
                    graph[dep].append(name)
                    indegree[name] += 1
            for after in skill.get("runs_after", []):
                if after in skill_nodes:
                    graph[after].append(name)
                    indegree[name] += 1
            for before in skill.get("runs_before", []):
                if before in skill_nodes:
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
            remaining = set(skill_nodes.keys()) - set(order)
            raise CyclicDependencyError(f"Circular dependency detected in skill manifest: {sorted(list(remaining))}")

        if available_skills is None:
            return order

        result = []
        for name in order:
            if name in available_skills:
                result.append(available_skills[name])
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skill '{name}' in manifest but not registered, skipping")
        return result

    @classmethod
    def from_manifest(
        cls,
        manifest_path: str,
        dependencies: dict[str, Any] | None = None,
        event_bus: Optional[EventBus] = None,
        correlation_id: Optional[str] = None,
        dag_scheduler: "DAGScheduler | None" = None,
        use_dag_scheduler: bool = False,
    ) -> "Orchestrator":
        """マニフェストYAMLからトポロジカル順序付きの実行Orchestratorインスタンスを構築する (Step 16, 20)"""
        import logging
        from src.agents.skill_base import validate_manifest, load_skill_from_spec, SkillManifestItem

        logger = logging.getLogger(__name__)
        manifest = validate_manifest(manifest_path)
        deps = dependencies or {}

        # 1. enabled なスキルのみを抽出 (Step 20)
        active_items: list[SkillManifestItem] = []
        for s in manifest.skills:
            if s.config.get("enabled", True):
                active_items.append(s)
            else:
                logger.info(f"Skill '{s.name}' is disabled in manifest config, skipping.")

        # 2. トポロジカルソートで順序を決定 (Step 15)
        item_dict = {item.name: item for item in active_items}
        from collections import defaultdict, deque

        graph = defaultdict(list)
        indegree = defaultdict(int)
        for item in active_items:
            name = item.name
            for dep in item.depends_on:
                if dep in item_dict:
                    graph[dep].append(name)
                    indegree[name] += 1
            for after in item.runs_after:
                if after in item_dict:
                    graph[after].append(name)
                    indegree[name] += 1
            for before in item.runs_before:
                if before in item_dict:
                    graph[name].append(before)
                    indegree[before] += 1

        queue = deque([name for name in item_dict if indegree[name] == 0])
        ordered_names: list[str] = []
        while queue:
            node = queue.popleft()
            ordered_names.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_names) != len(item_dict):
            remaining = set(item_dict.keys()) - set(ordered_names)
            raise CyclicDependencyError(f"Circular dependency detected in skill manifest: {sorted(list(remaining))}")

        # 3. 各スキルをインスタンス化
        skill_instances: dict[str, SkillAgent] = {}
        for name in ordered_names:
            item = item_dict[name]
            skill_instances[name] = load_skill_from_spec(item, event_bus=event_bus, **deps)

        # 4. ノード関数の構築
        nodes: dict[AgentName | str, AgentNode] = {}
        for idx, name in enumerate(ordered_names):
            instance = skill_instances[name]
            next_name = ordered_names[idx + 1] if idx + 1 < len(ordered_names) else None
            nodes[name] = _make_skill_node(instance, next_name)
            # 互換性のための小文字短縮名や AgentName キーも登録
            short_name = name.replace("Skill", "").replace("Agent", "").lower()
            nodes[short_name] = nodes[name]
            try:
                agent_enum = AgentName(short_name)
                nodes[agent_enum] = nodes[name]
            except ValueError:
                pass

        orch = cls(nodes=nodes, event_bus=event_bus, correlation_id=correlation_id, dag_scheduler=dag_scheduler, use_dag_scheduler=use_dag_scheduler)
        orch._ordered_skill_names = ordered_names
        orch._skill_instances = skill_instances
        orch._register_skills_to_scheduler()
        return orch

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
        
        import statistics
        
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

    async def run(self, ctx: AgentContext, start: AgentName | str | None = None) -> AgentContext:
        if start is None:
            if self._ordered_skill_names:
                current = self._ordered_skill_names[0]
            elif self.nodes:
                current = next(iter(self.nodes.keys()))
            else:
                raise ValueError("No registered nodes to execute in Orchestrator")
        else:
            current = start

        # If not using DAG scheduler, run the original logic
        if not self.use_dag_scheduler or not self.dag_scheduler:
            backtrack_counts: dict[str, int] = {}
        else:
            # Use DAG scheduler for execution
            # Task results cache: maps task_id to AgentResult (to access artifacts)
            task_results: dict[str, AgentResult] = {}
            
            # Register skills to scheduler with wrappers
            for skill_name, skill_instance in self._skill_instances.items():
                # Create a wrapper function for this skill
                def make_skill_wrapper(name: str, instance: SkillAgent):
                    async def wrapper(**kwargs):
                        # Extract task_id and input_from from kwargs
                        task_id = kwargs.get("task_id")
                        input_from = kwargs.get("input_from")
                        
                        # Publish start event
                        if self.event_bus:
                            await self.event_bus.publish_async(
                                AgentEvent(
                                    agent=name,
                                    payload={
                                        "status": "started",
                                        "ep_num": ctx.ep_num,
                                    },
                                    correlation_id=self.correlation_id,
                                )
                            )
                        
                        try:
                            # Determine input AgentContext
                            if input_from and input_from in task_results:
                                # Use previous task's output artifacts as input artifacts
                                prev_result = task_results[input_from]
                                input_artifacts = prev_result.artifacts.copy() if hasattr(prev_result, 'artifacts') else {}
                            else:
                                # First task or no input_from: use the original ctx's artifacts
                                input_artifacts = ctx.artifacts.copy()
                            
                            # Create input AgentContext
                            input_ctx = AgentContext(
                                book_id=ctx.book_id,
                                branch_id=ctx.branch_id,
                                ep_num=ctx.ep_num,
                                artifacts=input_artifacts,
                                backtrack_history=ctx.backtrack_history.copy(),  # Preserve original backtrack history
                            )
                            
                            # Execute the skill
                            agent_result: AgentResult = await instance.run(input_ctx)
                            
                            # Publish completion event
                            if self.event_bus:
                                await self.event_bus.publish_async(
                                    AgentEvent(
                                        agent=name,
                                        payload={
                                            "status": "completed" if agent_result.error is None else "failed",
                                            "ep_num": ctx.ep_num,
                                            "should_retry": agent_result.should_retry,
                                            "error": agent_result.error,
                                        },
                                        correlation_id=self.correlation_id,
                                    )
                                )
                            
                            # If the skill returned an error, treat it as a failure
                            if agent_result.error is not None:
                                raise RuntimeError(f"Skill {name} failed: {agent_result.error}")
                            
                            # Store the full result for potential use by subsequent tasks
                            if task_id:
                                task_results[task_id] = agent_result
                            
                            # For DAGScheduler, we return the artifacts to be merged into ctx.artifacts
                            # In the original flow, ctx.artifacts.update(result.artifacts) is done
                            return agent_result.artifacts
                        except Exception as e:
                            # Publish failure event for unexpected exceptions
                            if self.event_bus:
                                await self.event_bus.publish_async(
                                    AgentEvent(
                                        agent=name,
                                        payload={
                                            "status": "failed",
                                            "ep_num": ctx.ep_num,
                                            "should_retry": False,
                                            "error": str(e),
                                        },
                                        correlation_id=self.correlation_id,
                                    )
                                )
                            raise
                    
                    return wrapper
                
                wrapper = make_skill_wrapper(skill_name, skill_instance)
                self.dag_scheduler.register_task(skill_name, wrapper)
            
            # Build DAG from ordered skills
            graph = self._build_dag_graph()
            
            # Execute DAG using scheduler
            executed_graph = await self.dag_scheduler.run_dag(graph)
            
            # Collect results from completed nodes and update ctx.artifacts
            for task_id, node in executed_graph.nodes.items():
                if node.status == "completed" and node.result is not None:
                    # node.result is what our wrapper returned (artifacts dict)
                    if isinstance(node.result, dict):
                        ctx.artifacts.update(node.result)
                    else:
                        # If result is not a dict, store it with task_id as key
                        ctx.artifacts[task_id] = node.result
            
            return ctx
        while current:
            agent_key = current.value if hasattr(current, "value") else str(current)
            # ノード実行前イベント発行
            if self.event_bus:
                await self.event_bus.publish_async(
                    AgentEvent(
                        agent=agent_key,
                        payload={"status": "started", "ep_num": ctx.ep_num},
                        correlation_id=self.correlation_id,
                    )
                )

            node = self.nodes.get(current) or self.nodes.get(agent_key)
            if node is None:
                raise RuntimeError(f"Agent node not registered: {agent_key}")

            # フォールトトレラント: 個別スキル失敗を捕捉し、次のスキルへ継続可能にする
            try:
                result = await node(ctx)
                ctx.artifacts.update(result.artifacts)

                next_agent_val = (
                    result.next_agent.value
                    if hasattr(result.next_agent, "value")
                    else (str(result.next_agent) if result.next_agent is not None else None)
                )

                # ノード実行後イベント発行
                if self.event_bus:
                    await self.event_bus.publish_async(
                        AgentEvent(
                            agent=agent_key,
                            payload={
                                "status": "completed" if not result.error else "failed",
                                "ep_num": ctx.ep_num,
                                "next_agent": next_agent_val,
                                "should_retry": result.should_retry,
                                "error": result.error,
                            },
                            correlation_id=self.correlation_id,
                        )
                    )

                # Handle should_retry (backtrack or retry)
                if result.should_retry:
                    # Handle backtrack logic
                    current_agent_name = agent_key
                    # Increment backtrack count for this node
                    backtrack_counts[current_agent_name] = backtrack_counts.get(current_agent_name, 0) + 1
                    current_count = backtrack_counts[current_agent_name]

                    # Check if we exceeded max backtracks
                    if current_count > self.max_backtracks_per_node:
                        # Handle max backtrack exceeded: proceed to next node in pipeline rather than backtracking
                        ctx.artifacts[f"{current_agent_name}_max_backtrack_exceeded"] = True
                        node_keys = list(self.nodes.keys())
                        next_node_after_current = None
                        for idx, k in enumerate(node_keys):
                            k_val = k.value if hasattr(k, "value") else str(k)
                            if k == current or k_val == current_agent_name:
                                if idx + 1 < len(node_keys):
                                    next_node_after_current = node_keys[idx + 1]
                                break
                        current = next_node_after_current
                        continue
                    # Update artifacts with backtrack info
                    # Note: we are already updating artifacts with result.artifacts above, but we want to add specific backtrack info
                    ctx.artifacts["audit_score"] = result.artifacts.get("audit_score")
                    ctx.artifacts["audit_retry_count"] = current_count
                    ctx.artifacts["regeneration_directive"] = result.artifacts.get("regeneration_directive")
                    ctx.artifacts["audit_status"] = "rejected"
                    # Add to backtrack history
                    ctx.backtrack_history.append({
                        "from_node": current_agent_name,
                        "to_node": result.next_agent.value if hasattr(result.next_agent, "value") else str(result.next_agent),
                        "reason": "audit_failed",
                        "count": current_count
                    })
                    ctx.artifacts["backtrack_history"] = ctx.backtrack_history
                    # Publish agent.backtracked event
                    if self.event_bus:
                        await self.event_bus.publish_async(
                            AgentEvent(
                                agent=current_agent_name,
                                payload={
                                    "status": "backtracked",
                                    "ep_num": ctx.ep_num,
                                    "from": current_agent_name,
                                    "to": result.next_agent.value if hasattr(result.next_agent, "value") else str(result.next_agent),
                                    "count": current_count
                                },
                                correlation_id=self.correlation_id,
                            )
                        )
                    # Set current to the next_agent for backtrack
                    current = result.next_agent
                    continue
                if result.error:
                    # エラーが発生しても次のスキルへ継続するオプション（artifacts にエラー情報を残す）
                    ctx.artifacts[f"{agent_key}_error"] = result.error
                    if self.event_bus:
                        await self.event_bus.publish_async(
                            AgentEvent(
                                agent=agent_key,
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
                error_msg = f"Unexpected error in {agent_key}: {e}"
                ctx.artifacts[f"{agent_key}_exception"] = error_msg
                if self.event_bus:
                    await self.event_bus.publish_async(
                        AgentEvent(
                            agent=agent_key,
                            payload={
                                "status": "exception_continued",
                                "ep_num": ctx.ep_num,
                                "error": error_msg,
                            },
                            correlation_id=self.correlation_id,
                        )
                    )
                raise RuntimeError(error_msg)
        return ctx



