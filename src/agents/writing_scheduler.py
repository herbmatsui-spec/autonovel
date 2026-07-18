import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.core.observability import StructuredLogger, TraceContext
from src.core.interfaces import IPromptManager

logger = logging.getLogger(__name__)


class StreamingPlotScheduler:
    """エピソードのプロット生成をストリーミングスケジュール管理する"""
    def __init__(self, repo: Any, llm: Any, pm: IPromptManager, planner: Any, book_id: int, branch_id: int, arcs: List[Any], end_ep: int, reporter=None,
                 max_concurrent: int = 2, max_retries: int = 3, timeout: int = 60):
        self.repo = repo
        self.llm = llm
        self.pm = pm
        self.planner = planner
        self.book_id = book_id
        self.branch_id = branch_id
        self.arcs = arcs
        self.end_ep = end_ep
        self.reporter = reporter
        self.tasks = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self._max_retries = max_retries
        self._timeout = timeout
        self.metrics: Dict[str, int] = {
            "scheduled": 0, "completed": 0, "cancelled": 0,
            "cache_hits": 0, "cache_misses": 0,
            "late_deliveries": 0, "errors": 0,
            "retries": 0,
        }
        self._gen_times: List[float] = []
        self._gen_start_times: Dict[int, float] = {}
        self._task_priorities: Dict[int, int] = {}
        self._consecutive_errors: int = 0
        self._circuit_open: bool = False
        self._circuit_breaker_threshold: int = 5

    async def schedule_plot_generation(
        self, ep_num: int, bible: Any, settings: Dict[str, Any], depends_on: Optional[int] = None, priority: int = 5
    ):
        
        Args:
            ep_num: エピソード番号
            bible: ブックデータ
            settings: 設定辞書
            depends_on: このエピソードが依存するエピソード番号（省略可能）。
                例: depends_on=3 の場合、エピソード3のプロット生成完了を待つ。
        """
        if ep_num > self.end_ep:
            return
        if ep_num in self.tasks:
            return
        
        # 依存関係チェック: 依存先が存在し、まだタスクが完了していない場合は待機
        # 自己依存は無視（デッドロック防止）
        if (
            depends_on is not None
            and depends_on != ep_num  # 自己依存を防止
            and depends_on in self.tasks
        ):
            if self.reporter:
                self.reporter.report(
                    f"🔗 Ep.{ep_num} は Ep.{depends_on} 完了待ち", "debug"
                )
            await self.await_plot_ready(depends_on)
        
        self.metrics["scheduled"] += 1
        self._gen_start_times[ep_num] = asyncio.get_event_loop().time()
        self._task_priorities[ep_num] = priority

        async def _run_gen():
            try:
                # Check cache first
                cached = await self._check_cache(ep_num)
                if cached is not None:
                    self.metrics["cache_hits"] += 1
                    return cached
                
                # Generate with retry logic
                last_error = None
                for attempt in range(self._max_retries):
                    try:
                        if self.reporter:
                            self.reporter.report(f"🗺️ プロット先行生成スケジュール: 第{ep_num}話 (試行 {attempt+1})", "info")
                            results = await asyncio.wait_for(
                                self.planner.expand_plots(self.book_id, [ep_num], self.arcs, reporter=self.reporter,
                                branch_id=self.branch_id),
                                timeout=self._timeout
                                )
                            elapsed = asyncio.get_event_loop().time() - self._gen_start_times.get(ep_num, 0)
                            self._gen_times.append(elapsed)
                            if len(self._gen_times) > 10:
                                self._gen_times.pop(0)
                            if elapsed > 30 and self.reporter:
                                self.reporter.report(f"⏰ Ep.{ep_num} プロット生成長時間化 ({elapsed:.1f}s)", "warning")
                            return results[0]
                    except asyncio.CancelledError:
                        if self.reporter:
                            self.reporter.report(f"🔄 Ep.{ep_num} はキャンセルされました", "debug")
                        raise
                    except asyncio.TimeoutError:
                        if self.reporter:
                            self.reporter.report(f"⏱️ Ep.{ep_num} タイムアウト ({self._timeout}s)", "error")
                        last_error = asyncio.TimeoutError(f"Timeout after {self._timeout}s")
                        self.metrics["errors"] += 1
                        self.metrics["retries"] += 1
                        if attempt < self._max_retries - 1:
                            backoff_sec = min(30, 2 ** attempt)
                            if self.reporter:
                                self.reporter.report(
                                    f"🔄 Ep.{ep_num} リトライ {attempt+1}/{self._max_retries} ({backoff_sec}s後): タイムアウト", "warning")
                            await asyncio.sleep(backoff_sec)
                    except Exception as e:
                        last_error = e
                        self.metrics["errors"] += 1
                        self.metrics["retries"] += 1
                        if attempt < self._max_retries - 1:
                            backoff_sec = min(30, 2 ** attempt)
                            if self.reporter:
                                self.reporter.report(
                                    f"🔄 Ep.{ep_num} リトライ {attempt+1}/{self._max_retries} ({backoff_sec}s後): {e}", "warning")
                            await asyncio.sleep(backoff_sec)
                
                if last_error and self.reporter:
                    self.reporter.report(f"❌ Ep.{ep_num} 最終失敗: {last_error}", "error")
                return None
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.metrics["errors"] += 1
                StructuredLogger.error("Failed scheduled plot gen", trace_id=TraceContext.get_trace_id(), error=e)
                return None

            finally:
                self._gen_start_times.pop(ep_num, None)
                self._task_priorities.pop(ep_num, None)
        self.tasks[ep_num] = asyncio.create_task(_run_gen())

    async def await_plot_ready(self, ep_num: int) -> Optional[Any]:
        if ep_num not in self.tasks:
            self.metrics["cache_misses"] += 1
            return await self.repo.get_plot(self.branch_id, ep_num)
        task = self.tasks[ep_num]
        if not task.done():
            if self.reporter:
                self.reporter.report(f"⏳ 第{ep_num}話: プロット生成待機中...", "debug")
            self.metrics["late_deliveries"] += 1
        try:
            result = await task
        except asyncio.CancelledError:
            self.metrics["cache_misses"] += 1
            return await self.repo.get_plot(self.branch_id, ep_num)
        self.tasks.pop(ep_num, None)
        if result is not None:
            self.metrics["completed"] += 1
        return result

    async def _check_cache(self, ep_num: int) -> Optional[Any]:
        plot = await self.repo.get_plot(self.branch_id, ep_num)
        if plot and plot.detailed_blueprint and len(plot.detailed_blueprint) > 50:
            fut = asyncio.Future()
            fut.set_result(plot)
            self.tasks[ep_num] = fut
            return plot
        return None

    async def cancel_range(self, start_ep: int, end_ep: int) -> int:
        cancelled = 0
        for ep_num in list(self.tasks.keys()):
            if start_ep <= ep_num <= end_ep:
                task = self.tasks.pop(ep_num, None)
                self._task_priorities.pop(ep_num, None)
                if task is not None and not task.done():
                    task.cancel()
                    cancelled += 1
                    self.metrics["cancelled"] += 1
        return cancelled

    async def cancel_all(self) -> int:
        self._task_priorities.clear()
        return await self.cancel_range(1, self.end_ep)

    def pending_episodes(self) -> List[int]:
        pending = [ep for ep, t in self.tasks.items() if not t.done()]
        pending.sort(key=lambda ep: self._task_priorities.get(ep, 5))
        return pending

    def get_metrics(self) -> Dict[str, int]:
        return dict(self.metrics)

    def get_latencies(self) -> Dict[str, float]:
        gen_avg = sum(self._gen_times) / max(1, len(self._gen_times))
        return {"gen_avg_sec": gen_avg}