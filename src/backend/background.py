"""
background.py - バックグラウンド処理・進捗管理モジュール
スレッドセーフな進捗状態 (ProgressState) と DB 保存処理を定義。
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SaveStrategy(ABC):
    @abstractmethod
    def save(self, state: "ProgressState", state_json: str, now: str) -> None:
        ...


class RedisSaveStrategy(SaveStrategy):
    def save(self, state: "ProgressState", state_json: str, now: str) -> None:
        from src.backend.redis_util import get_redis_client
        redis_client = get_redis_client()
        if redis_client is None:
            raise RuntimeError("Redis client is not available")
        try:
            redis_client.set(f"task_status:{state.task_id}", state_json, ex=86400)
            redis_client.publish(f"task_events:{state.task_id}", state_json)
        except Exception as e:
            logger.error(f"[ProgressState] Failed to save to Redis: {e}")
            raise


class AsyncDbSaveStrategy(SaveStrategy):
    def save(self, state: "ProgressState", state_json: str, now: str) -> None:
        if state.repo is None:
            return
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(state.repo.db.save_internal_state(f"task_status:{state.task_id}", state_json, now))
            task.add_done_callback(lambda t: logger.error(f"[ProgressState] DB Save error: {t.exception()}") if not t.cancelled() and t.exception() else None)
        except RuntimeError:
            raise RuntimeError("No running event loop for async DB save")


class SyncDbSaveStrategy(SaveStrategy):
    def save(self, state: "ProgressState", state_json: str, now: str) -> None:
        if state.repo is None:
            return
        try:
            state.repo.save_internal_state_sync(
                f"task_status:{state.task_id}", state_json
            )
        except Exception as e:
            logger.error(f"[ProgressState] Sync DB save failed: {e}")


class NoOpSaveStrategy(SaveStrategy):
    def save(self, state: "ProgressState", state_json: str, now: str) -> None:
        pass


def _select_strategy(state: "ProgressState") -> SaveStrategy:
    from src.backend.redis_util import get_redis_client
    redis_client = get_redis_client()
    if redis_client is not None:
        return RedisSaveStrategy()
    if state.repo is None:
        return NoOpSaveStrategy()
    try:
        asyncio.get_running_loop()
        return AsyncDbSaveStrategy()
    except RuntimeError:
        return SyncDbSaveStrategy()


# ==========================================
# ProgressState（スレッドセーフな進捗状態）
# ==========================================
class ProgressState:
    """UIとバックグラウンド処理を繋ぐスレッド安全な進捗状態"""
    def __init__(
        self,
        is_running: bool = False,
        task_id: Optional[str] = None,
        repo: Optional[Any] = None,
        skip_initial_save: bool = False
    ):
        self.is_running    = is_running
        self.task_id       = task_id or f"task_{int(time.time())}"
        self.repo          = repo
        self.current_step  = 0
        self.total_steps   = 0
        self.message       = "準備中..."
        self.sub_message   = ""
        self.streaming_text = ""
        self.logs          = []
        self.error         = None
        self.result_data   = None
        self.start_time    = time.time()
        self.last_updated  = time.time()
        self._stop_event   = threading.Event()
        # スレッド間でのトークン受け渡し用
        self.token_usage   = {"prompt": 0, "completion": 0, "calls": 0}
        self._save_strategy = _select_strategy(self)

        if not skip_initial_save:
            self._save_to_db()

    def stop(self) -> None:
        """処理の中断を要求する"""
        self._stop_event.set()
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] 🛑 ユーザーにより停止命令が出されました。")
        self._save_to_db()

    def should_stop(self) -> bool:
        """中断命令が出ているか確認する"""
        if self._stop_event.is_set():
            return True

        # Rate-limit Redis/DB check to once every 1.5 seconds to avoid performance degradation
        now = time.time()
        if not hasattr(self, "_last_stop_check") or now - self._last_stop_check > 1.5:
            self._last_stop_check = now
            from src.backend.redis_util import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                try:
                    val = redis_client.get(f"task_status:{self.task_id}")
                    if val:
                        import json
                        state_dict = json.loads(val)
                        if not state_dict.get("is_running", True):
                            self._stop_event.set()
                            return True
                except Exception:
                    pass
        return self._stop_event.is_set()

    def _save_to_db(self) -> None:
        if not self.task_id:
            return

        state_dict = {
            "is_running": self.is_running,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "message": self.message,
            "sub_message": self.sub_message,
            "streaming_text": self.streaming_text,
            "logs": self.logs,
            "error": self.error,
            "result_data": self.result_data,
            "token_usage": self.token_usage,
            "start_time": self.start_time,
            "last_updated": self.last_updated
        }

        class StateEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bytes):
                    return "<bytes>"
                try:
                    return super().default(obj)
                except TypeError:
                    return str(obj)

        state_json = json.dumps(state_dict, cls=StateEncoder)
        now = datetime.datetime.now().isoformat()
        self._save_strategy.save(self, state_json, now)

    def update(
        self,
        message: str,
        sub_message: str = "",
        step: Optional[int] = None,
        total: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        display_msg = message
        full_msg = f"{display_msg}: {sub_message}" if sub_message else display_msg

        clean_full_msg = full_msg.strip()
        if not self.logs or self.logs[-1].split("] ", 1)[-1].strip() != clean_full_msg:
            self.logs.append(f"[{time.strftime('%H:%M:%S')}] {full_msg}")
        self.message     = message
        self.sub_message = sub_message
        if step is not None:
            self.current_step = step
        if total is not None:
            self.total_steps = total
        self.last_updated = time.time()
        if error is not None:
            self.error = error
        self._save_to_db()


# ==========================================
# BackgroundReporter（ProgressStateを更新するレポーター）
# ==========================================
class BackgroundReporter:
    """バックグラウンドスレッドから ProgressState を更新する"""

    def __init__(self, state: ProgressState):
        self.state = state
        from src.core.observability import get_structured_logger
        self.logger = get_structured_logger("BackgroundReporter")

    def report(self, message: str, level: str = "info") -> None:
        if self.state.should_stop():
            return

        if level == "error":
            self.logger.error(message)
            self.state.update(message=f"🚨 {message}", error=message)
        elif level == "warning":
            self.logger.warning(message)
            self.state.update(message=f"⚠️ {message}")
        else:
            self.logger.info(message)
            self.state.update(message=f"ℹ️ {message}")

    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None:
        if self.state.should_stop():
            return
        self.state.update(text, sub_message=sub_text, step=current, total=total)

    def update_streaming_text(self, text: str) -> None:
        if self.state.should_stop():
            return
        # ストリーミングテキストを更新し、即座にRedis/DBへ保存してUIに反映させる
        self.state.streaming_text = text
        self.state._save_to_db()

    def report_exception(self, e: Exception, context: str = "") -> None:
        """例外をキャッチしてエラーとして報告する"""
        error_msg = f"{context} - {type(e).__name__}: {str(e)}" if context else f"{type(e).__name__}: {str(e)}"
        self.logger.exception(f"Unhandled exception in background task: {error_msg}")
        self.state.update(message="🚨 エラーが発生しました", error=error_msg)


# Definitions moved to shared/utils.py


# ==========================================
# StatusReporter（レポーター基底クラス）
# ==========================================
class StatusReporter:
    """
    UI / CLI へのフィードバックを抽象化するレポーターの基底クラス。

    src/shared/utils.StatusReporter は Protocol（構造的子集型）として定義されており、
    実際の具象クラス（CLIStatusReporter 等）はこのクラスを継承して report / update_progress /
    update_streaming_text を実装する。ここでは最小実装を提供し、サブクラスで上書きする前提。
    """

    def __init__(self, state: Optional[ProgressState] = None):
        self.state = state

    def report(self, message: str, level: str = "info") -> None:
        """メッセージを出力する（サブクラスで上書き想定）。"""
        print(f"[{level.upper()}] {message}")

    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None:
        """進捗を更新する（サブクラスで上書き想定）。"""
        if self.state is not None:
            self.state.update(text, sub_message=sub_text, step=current, total=total)

    def update_streaming_text(self, text: str) -> None:
        """ストリーミングテキストを更新する（サブクラスで上書き想定）。"""
        if self.state is not None:
            self.state.streaming_text = text
            self.state._save_to_db()

    def report_exception(self, e: Exception, context: str = "") -> None:
        """例外をキャッチしてエラーとして報告する。"""
        error_msg = f"{context} - {type(e).__name__}: {str(e)}" if context else f"{type(e).__name__}: {str(e)}"
        self.report(error_msg, level="error")
