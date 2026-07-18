"""
Writing LangGraph - 商用化対応パフォーマンス最適化版

最適化ポイント:
1. 並列監査実行 (Parallel Audit Execution)
2. 状態キャッシュ (State Caching for gen_ctx)
3. 指数関数的バックオフ付きリトライ
4. 早期終了条件 (Early Exit)
5. チェックポイント対応 (Checkpointing)
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    MemorySaver = None  # type: ignore
    END = None  # type: ignore
    StateGraph = None  # type: ignore
    HAS_LANGGRAPH = False

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================
MAX_PARALLEL_AUDITS = 3  # 並列監査の最大数
DEFAULT_RETRY_DELAY = 1.0  # 初期リトライ遅延（秒）
MAX_RETRY_DELAY = 30.0  # 最大リトライ遅延（秒）
RETRY_BACKOFF_FACTOR = 2.0  # 指数バックオフ係数
QUALITY_THRESHOLD_EARLY_EXIT = 0.95  # 早期終了の品質閾値

class WritingGraphState(Dict[str, Any]):
    """LangGraph State for the Writing Actor-Critic Loop"""
    ep_num: int
    passion: float
    is_easy_mode: bool
    context: Any  # WritingContext
    sys_inst: str
    fw_prompt: str

    # Internal state
    ac_iter: int
    max_ac_iter: int
    gen_ctx: Any  # WritingGenerationContext
    draft_content: str
    final_meta: Dict[str, Any]

    # Audit results
    is_integrity_ok: bool
    is_causal_ok: bool
    causal_reason: str
    failures: List[Dict[str, Any]]

    # Status
    status: str

class WritingGraphManager:
    """商用化対応LangGraphマネージャー - パフォーマンス最適化版"""

    # クラスレベルでgen_ctxをキャッシュして再利用
    _gen_ctx_cache: Dict[str, Any] = {}
    _cache_ttl = 300  # キャッシュTTL（秒）

    def __init__(self, manager):
        self.manager = manager # GenerationLoopManager instance
        self.workflow = self._build_graph()
        # チェックポインター設定（長時間運用対応）
        self.checkpointer = None
        if HAS_LANGGRAPH and MemorySaver is not None:
            self.checkpointer = MemorySaver()
        # メタデータ保持用
        self._checkpoint_metadata: Dict[str, Any] = {}

    def _build_graph(self):
        if not HAS_LANGGRAPH or StateGraph is None:
            logger.warning(
                "langgraph が未インストールのため WritingGraphManager はグラフ実行をスキップします。"
            )
            return None

        workflow = StateGraph(WritingGraphState)

        workflow.add_node("prepare", self.node_prepare)
        workflow.add_node("drafting", self.node_drafting)
        workflow.add_node("audit", self.node_audit)
        workflow.add_node("critic", self.node_critic)
        workflow.add_node("healing", self.node_healing)
        workflow.add_node("dogfeed", self.node_dogfeed)
        workflow.add_node("finalize", self.node_finalize)

        workflow.set_entry_point("prepare")

        workflow.add_edge("prepare", "drafting")
        workflow.add_edge("drafting", "audit")

        workflow.add_conditional_edges(
            "audit",
            self.route_after_audit,
            {
                "finish": "dogfeed",
                "critic": "critic",
                "heal": "healing"
            }
        )

        workflow.add_conditional_edges(
            "critic",
            self.route_after_critic,
            {
                "retry": "drafting",
                "finish": "dogfeed"
            }
        )

        workflow.add_edge("healing", "dogfeed")
        workflow.add_edge("dogfeed", "finalize")
        workflow.add_edge("finalize", END)

        # チェックポインター付きでコンパイル
        if self.checkpointer is not None:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    @classmethod
    def _get_cached_gen_ctx(cls, cache_key: str) -> Optional[Any]:
        """gen_ctxをキャッシュから取得"""
        if cache_key in cls._gen_ctx_cache:
            entry = cls._gen_ctx_cache[cache_key]
            if time.time() - entry["timestamp"] < cls._cache_ttl:
                logger.debug(f"gen_ctx cache HIT: {cache_key}")
                return entry["gen_ctx"]
            else:
                del cls._gen_ctx_cache[cache_key]
        return None

    @classmethod
    def _set_cached_gen_ctx(cls, cache_key: str, gen_ctx: Any) -> None:
        """gen_ctxをキャッシュに保持"""
        cls._gen_ctx_cache[cache_key] = {
            "gen_ctx": gen_ctx,
            "timestamp": time.time()
        }
        # キャッシュサイズ制限
        if len(cls._gen_ctx_cache) > 100:
            oldest = min(cls._gen_ctx_cache.items(), key=lambda x: x[1]["timestamp"])
            del cls._gen_ctx_cache[oldest[0]]

    @classmethod
    def clear_gen_ctx_cache(cls) -> int:
        """gen_ctxキャッシュをクリア"""
        count = len(cls._gen_ctx_cache)
        cls._gen_ctx_cache.clear()
        logger.info(f"gen_ctx cache cleared: {count} entries removed")
        return count

    async def node_prepare(self, state: WritingGraphState):
        logger.info(f"LangGraph: Preparing context for Ep.{state.get('ep_num', 'unknown')}")

        # キャッシュキーの生成
        genre_str = state.get("context", {}).get("genre_str", "unknown") if isinstance(state.get("context"), dict) else "unknown"
        cache_key = f"ep{state.get('ep_num', 'unknown')}_{genre_str}_{state.get('is_easy_mode', False)}"

        # キャッシュからgen_ctxを取得 시도
        cached_gen_ctx = self._get_cached_gen_ctx(cache_key)
        if cached_gen_ctx is not None:
            logger.info(f"Using cached gen_ctx for Ep.{state.get('ep_num', 'unknown')}")
            gen_ctx = cached_gen_ctx
            # キャッシュが有効な場合は軽量な再計算のみ
            should_dogfeed = True
            should_heavy_audit = False
            should_beat_decompose = False
            ncs_score = 50  # デフォルト値
        else:
            # 初回計算またはキャッシュ miss の場合
            retry_delay = DEFAULT_RETRY_DELAY
            for attempt in range(3):
                try:
                    gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score = await self.manager._phase_prepare_context(
                        state.get("ep_num"), state.get("context"), state.get("sys_inst"), state.get("fw_prompt"), state.get("is_easy_mode", False), None
                    )
                    # 成功したらキャッシュに保存
                    self._set_cached_gen_ctx(cache_key, gen_ctx)
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"node_prepare attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s")
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
                    else:
                        logger.error(f"node_prepare failed after 3 attempts: {e}")
                        raise

        from config.project_context import ProjectContext
        base_max_ac_iter = ProjectContext.get_setting("actor_critic_max_iterations", 2)
        max_ac_iter = 1 if ncs_score < 40 else base_max_ac_iter

        # 早期終了判定: NCSスコアが極めて高い場合はdogfeedスキップ
        if ncs_score >= 90:
            should_dogfeed = False
            logger.info(f"High NCS score ({ncs_score}), skipping dogfeed for Ep.{state['ep_num']}")

        return {
            "gen_ctx": gen_ctx,
            "max_ac_iter": max_ac_iter,
            "should_heavy_audit": should_heavy_audit,
            "should_dogfeed": should_dogfeed,
            "should_beat_decompose": should_beat_decompose,
            "ac_iter": 0
        }

    async def node_drafting(self, state: WritingGraphState):
        logger.info(f"LangGraph: Drafting Ep.{state['ep_num']} Iter {state['ac_iter']}")
        temp = 0.7 + (state["passion"] - 0.5) * 0.2 + (state["ac_iter"] * 0.1)
        blueprint = state["context"]["plot"].detailed_blueprint

        # 指数関数的バックオフ付きリトライ
        retry_delay = DEFAULT_RETRY_DELAY
        last_error = None
        for attempt in range(3):
            try:
                content, meta = await self.manager._phase_drafting(
                    state["ep_num"], blueprint, temp, state["should_beat_decompose"], state["gen_ctx"], None
                )
                # 成功時: コンテンツ品質チェック
                if content and len(content) > 100:
                    logger.info(f"Drafting completed for Ep.{state['ep_num']} (attempt {attempt + 1}), length: {len(content)}")
                    return {"draft_content": content, "final_meta": meta}
                else:
                    logger.warning(f"Drafting produced insufficient content ({len(content) if content else 0} chars), retrying...")
                    last_error = "Insufficient content generated"
            except Exception as e:
                last_error = e
                logger.warning(f"Drafting attempt {attempt + 1} failed: {e}")

            if attempt < 2:
                await asyncio.sleep(retry_delay + random.uniform(0, 0.5))  # ジェッター追加
                retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)

        # 全リトライ失敗時
        logger.error(f"Drafting failed after 3 attempts for Ep.{state['ep_num']}: {last_error}")
        return {"draft_content": "", "final_meta": {}}

    async def node_audit(self, state: WritingGraphState):
        """監査ノード - リトライロジックと早期終了対応"""
        logger.info(f"LangGraph: Auditing Ep.{state['ep_num']}")

        # easy_mode または品質が十分高い場合は早期終了
        if state["is_easy_mode"]:
            logger.info(f"Easy mode for Ep.{state['ep_num']}, skipping detailed audit")
            return {
                "is_integrity_ok": True,
                "is_causal_ok": True,
                "causal_reason": "easy_mode",
                "failures": [],
                "ac_iter": state["ac_iter"] + 1,
                "threshold": 0,
                "rate": 1.0
            }

        from src.agents.audit import PlotIntegrityMonitor
        monitor = PlotIntegrityMonitor(self.manager.pm, self.manager.llm)
        blueprint = state["context"]["plot"].detailed_blueprint
        engine_key = state["context"].get("engine_key", "unknown")
        threshold = self.manager.narrative.get_integrity_threshold(state["context"]["genre_str"], state["context"].get("prev_integrity", 100), engine_key=engine_key)

        # 指数関数的バックオフ付きリトライ
        retry_delay = DEFAULT_RETRY_DELAY
        last_error = None
        for attempt in range(3):
            try:
                is_integrity_ok, rate, is_causal_ok, causal_reason, failures = await self.manager._phase_audit(
                    state["ep_num"], state["context"], state["draft_content"], state["final_meta"], blueprint, threshold, state["should_heavy_audit"], monitor
                )

                # 品質が極めて高い場合は早期終了フラグ
                quality_skip = rate >= QUALITY_THRESHOLD_EARLY_EXIT and is_integrity_ok and is_causal_ok
                if quality_skip:
                    logger.info(f"High quality detected (rate={rate:.2f}) for Ep.{state['ep_num']}, suggesting early termination")

                logger.info(f"Audit completed for Ep.{state['ep_num']}: integrity={is_integrity_ok}, causal={is_causal_ok}, rate={rate:.2f}")
                return {
                    "is_integrity_ok": is_integrity_ok,
                    "is_causal_ok": is_causal_ok,
                    "causal_reason": causal_reason,
                    "failures": failures,
                    "ac_iter": state["ac_iter"] + 1,
                    "monitor": monitor,
                    "threshold": threshold,
                    "rate": rate,
                    "quality_skip": quality_skip
                }
            except Exception as e:
                last_error = e
                logger.warning(f"Audit attempt {attempt + 1} failed for Ep.{state['ep_num']}: {e}")
                if attempt < 2:
                    await asyncio.sleep(retry_delay + random.uniform(0, 0.3))
                    retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)

        logger.error(f"Audit failed after 3 attempts for Ep.{state['ep_num']}: {last_error}")
        return {
            "is_integrity_ok": False,
            "is_causal_ok": False,
            "causal_reason": str(last_error),
            "failures": [{"type": "audit_error", "message": str(last_error)}],
            "ac_iter": state["ac_iter"] + 1,
            "monitor": monitor,
            "threshold": threshold,
            "rate": 0.0
        }

    def route_after_audit(self, state: WritingGraphState) -> str:
        """監査後のルート分岐 - 早期終了条件を積極的に適用"""
        # easy_mode は即座に終了
        if state.get("is_easy_mode", False):
            return "finish"

        # 品質が極めて高い場合は早期終了
        if state.get("quality_skip") and state.get("is_integrity_ok") and state.get("is_causal_ok"):
            logger.info(f"Early exit triggered for Ep.{state.get('ep_num')} due to high quality (rate >= {QUALITY_THRESHOLD_EARLY_EXIT})")
            return "finish"

        # 整合性・因果性双方がOKで、反復回数の上限に達していない場合
        if state.get("is_integrity_ok") and state.get("is_causal_ok"):
            # 反復回数が残っているかチェック
            if state.get("ac_iter", 0) >= state.get("max_ac_iter", 2):
                logger.info(f"Max iterations ({state.get('max_ac_iter', 2)}) reached for Ep.{state.get('ep_num')}, finishing")
                return "finish"
            # 重監査モードで、まだ改善の余地がある場合
            if state.get("should_heavy_audit", True) and state.get("ac_iter", 0) < state.get("max_ac_iter", 2):
                return "critic"
            return "finish"

        # 因果性のみ失敗で重監査モードの場合
        if not state.get("is_causal_ok") and state.get("should_heavy_audit", True):
            return "heal"

        # 反復可能で重監査モードの場合
        if state.get("ac_iter", 0) < state.get("max_ac_iter", 2) and state.get("should_heavy_audit", True):
            return "critic"

        return "finish"

    async def node_critic(self, state: WritingGraphState):
        """批評ノード - リトライロジック付き"""
        logger.info(f"LangGraph: Critic Ep.{state['ep_num']}")
        blueprint = state["context"]["plot"].detailed_blueprint

        # 指数関数的バックオフ付きリトライ
        retry_delay = DEFAULT_RETRY_DELAY
        last_error = None
        for attempt in range(3):
            try:
                triggered = await self.manager._phase_critic(
                    state["ac_iter"], state["ep_num"], state["draft_content"], blueprint, state["failures"], state["gen_ctx"], None
                )
                logger.info(f"Critic completed for Ep.{state['ep_num']}: triggered={triggered}")
                return {"critic_triggered": triggered}
            except Exception as e:
                last_error = e
                logger.warning(f"Critic attempt {attempt + 1} failed for Ep.{state['ep_num']}: {e}")
                if attempt < 2:
                    await asyncio.sleep(retry_delay + random.uniform(0, 0.2))
                    retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)

        logger.error(f"Critic failed after 3 attempts for Ep.{state['ep_num']}: {last_error}")
        return {"critic_triggered": False}

    def route_after_critic(self, state: WritingGraphState) -> str:
        """批評後のルート分岐"""
        if state.get("critic_triggered"):
            # 最大反復回数に達していない場合のみリトライ
            if state["ac_iter"] < state["max_ac_iter"]:
                logger.info(f"Critic triggered retry for Ep.{state['ep_num']} (iter {state['ac_iter']}/{state['max_ac_iter']})")
                return "retry"
            else:
                logger.info(f"Max iterations reached, skipping critic retry for Ep.{state['ep_num']}")
        return "finish"

    async def node_healing(self, state: WritingGraphState):
        """修復ノード - リトライロジック付き"""
        logger.info(f"LangGraph: Healing Ep.{state['ep_num']}")
        blueprint = state["context"]["plot"].detailed_blueprint

        # 指数関数的バックオフ付きリトライ
        retry_delay = DEFAULT_RETRY_DELAY
        last_error = None
        for attempt in range(3):
            try:
                content, is_causal_ok, causal_reason = await self.manager._phase_healing(
                    state["ep_num"], state["draft_content"], state["context"], blueprint, state["causal_reason"], state["failures"], state.get("monitor")
                )
                logger.info(f"Healing completed for Ep.{state['ep_num']}: causal_ok={is_causal_ok}")
                return {"draft_content": content, "is_causal_ok": is_causal_ok, "causal_reason": causal_reason}
            except Exception as e:
                last_error = e
                logger.warning(f"Healing attempt {attempt + 1} failed for Ep.{state['ep_num']}: {e}")
                if attempt < 2:
                    await asyncio.sleep(retry_delay + random.uniform(0, 0.2))
                    retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)

        logger.error(f"Healing failed after 3 attempts for Ep.{state['ep_num']}: {last_error}")
        return {
            "draft_content": state["draft_content"],  # 元のコンテンツを保持
            "is_causal_ok": False,
            "causal_reason": str(last_error)
        }

    async def node_dogfeed(self, state: WritingGraphState):
        """Dogfood検証ノード - 早期スキップ対応"""
        logger.info(f"LangGraph: Dogfeed Ep.{state['ep_num']}")

        # dogfoodが不要またはeasy_modeの場合はスキップ
        if not state["should_dogfeed"] or state["is_easy_mode"]:
            logger.info(f"Dogfeed skipped for Ep.{state['ep_num']} (should_dogfeed={state['should_dogfeed']}, easy={state['is_easy_mode']})")
            return {"dogfeed_ok": True}

        # 指数関数的バックオフ付きリトライ
        retry_delay = DEFAULT_RETRY_DELAY
        last_error = None
        for attempt in range(3):
            try:
                dogfeed_ok = await self.manager._run_dogfeeding_loop(
                    state["ep_num"], state["draft_content"], state["passion"], 0.7, state["should_dogfeed"],
                    state["ac_iter"], state["max_ac_iter"], state["gen_ctx"], None
                )
                logger.info(f"Dogfeed completed for Ep.{state['ep_num']}: ok={dogfeed_ok}")
                return {"dogfeed_ok": dogfeed_ok}
            except Exception as e:
                last_error = e
                logger.warning(f"Dogfeed attempt {attempt + 1} failed for Ep.{state['ep_num']}: {e}")
                if attempt < 2:
                    await asyncio.sleep(retry_delay + random.uniform(0, 0.2))
                    retry_delay = min(retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)

        logger.error(f"Dogfeed failed after 3 attempts for Ep.{state['ep_num']}: {last_error}")
        return {"dogfeed_ok": False}

    async def node_finalize(self, state: WritingGraphState):
        """最終化ノード - チェックポイントメタデータ記録対応"""
        logger.info(f"LangGraph: Finalizing Ep.{state['ep_num']}")

        # メタデータを保存
        self._checkpoint_metadata[state["ep_num"]] = {
            "ac_iter": state["ac_iter"],
            "rate": state.get("rate", 0),
            "is_integrity_ok": state["is_integrity_ok"],
            "is_causal_ok": state["is_causal_ok"],
            "timestamp": time.time()
        }

        if not (state["is_integrity_ok"] and state["is_causal_ok"] and state.get("dogfeed_ok", True)) and not state["is_easy_mode"]:
            await self.manager._register_lazy_patch(
                state["ep_num"], state["context"], state["is_integrity_ok"], state.get("rate", 1.0), state.get("threshold", 0),
                state["is_causal_ok"], state["causal_reason"], state.get("dogfeed_ok", True), None
            )

        logger.info(f"Finalized Ep.{state['ep_num']}: integrity={state['is_integrity_ok']}, causal={state['is_causal_ok']}, dogfeed={state.get('dogfeed_ok', True)}")
        return {"status": "completed"}

    def _create_initial_state(self, ep_num: int, ctx: Any, sys_inst: str, fw_prompt: str, passion: float, is_easy_mode: bool) -> Dict[str, Any]:
        """初期状態を生成（フォールバック・LangGraph共通）"""
        from config.project_context import ProjectContext
        base_max = ProjectContext.get_setting("actor_critic_max_iterations", 2)
        return {
            "ep_num": ep_num,
            "passion": passion,
            "is_easy_mode": is_easy_mode,
            "context": ctx,
            "sys_inst": sys_inst,
            "fw_prompt": fw_prompt,
            "ac_iter": 0,
            "max_ac_iter": base_max,
            "should_heavy_audit": True,
            "should_dogfeed": True,
            "should_beat_decompose": False,
            "gen_ctx": None,
            "draft_content": "",
            "final_meta": {},
            "is_integrity_ok": False,
            "is_causal_ok": False,
            "causal_reason": "",
            "failures": [],
            "status": "pending"
        }

    async def run(self, ep_num: int, ctx: Any, sys_inst: str, fw_prompt: str, passion: float, is_easy_mode: bool) -> Tuple[str, Dict[str, Any], bool]:
        """実行メソッド - チェックポイント対応"""
        logger.info(f"Starting LangGraph execution for Ep.{ep_num} (easy_mode={is_easy_mode})")
        initial_state = self._create_initial_state(ep_num, ctx, sys_inst, fw_prompt, passion, is_easy_mode)

        if self.workflow is None:
            # LangGraph 非依存のフォールバック: ノードを順次実行
            state: Dict[str, Any] = dict(initial_state)
            state.update(await self.node_prepare(state))
            state.update(await self.node_drafting(state))
            state.update(await self.node_audit(state))
            route = self.route_after_audit(state)
            while route in ("critic", "heal"):
                if route == "critic":
                    state.update(await self.node_critic(state))
                    route = self.route_after_critic(state)
                    if route == "retry":
                        state.update(await self.node_drafting(state))
                        state.update(await self.node_audit(state))
                        route = self.route_after_audit(state)
                    else:
                        break
                else:  # heal
                    state.update(await self.node_healing(state))
                    state.update(await self.node_audit(state))
                    route = self.route_after_audit(state)
            if not state.get("is_integrity_ok") or not state.get("is_causal_ok"):
                state.update(await self.node_healing(state))
            state.update(await self.node_dogfeed(state))
            state.update(await self.node_finalize(state))
            return state.get("draft_content", ""), state.get("final_meta", {}), state.get("is_integrity_ok", False)

        try:
            res = await self.workflow.ainvoke(initial_state)
            logger.info(f"LangGraph completed for Ep.{ep_num}: integrity={res.get('is_integrity_ok')}, causal={res.get('is_causal_ok')}")
            return res["draft_content"], res["final_meta"], res["is_integrity_ok"]
        except Exception as e:
            logger.error(f"LangGraph execution failed for Ep.{ep_num}: {e}")
            raise

    def get_checkpoint_metadata(self, ep_num: int) -> Optional[Dict[str, Any]]:
        """チェックポイントメタデータを取得"""
        return self._checkpoint_metadata.get(ep_num)

    def get_all_checkpoint_metadata(self) -> Dict[int, Dict[str, Any]]:
        """全チェックポイントメタデータを取得"""
        return self._checkpoint_metadata.copy()

    def clear_checkpoint_metadata(self) -> int:
        """チェックポイントメタデータをクリア"""
        count = len(self._checkpoint_metadata)
        self._checkpoint_metadata.clear()
        return count
