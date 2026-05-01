"""
background.py - バックグラウンド処理・進捗管理モジュール
スレッドセーフな進捗状態 (ProgressState) と
バックグラウンドで非同期タスクを実行するユーティリティを集約。
"""
from __future__ import annotations
import asyncio
import logging
import threading
import time
from typing import Any, Callable, Literal, Optional, Protocol

from config import COST_INPUT_FLASH, COST_OUTPUT_FLASH
from streamlit.runtime.scriptrunner import add_script_run_ctx

logger = logging.getLogger(__name__)


# ==========================================
# StatusReporter プロトコル（UIと処理層を分離）
# ==========================================
class StatusReporter(Protocol):
    """UIへのフィードバックを抽象化するインターフェース"""
    def report(self, message: str, level: Literal["info", "warning", "error"] = "info") -> None: ...
    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None: ...


# ==========================================
# ProgressState（スレッドセーフな進捗状態）
# ==========================================
class ProgressState:
    """UIとバックグラウンド処理を繋ぐスレッド安全な進捗状態"""
    def __init__(self, is_running: bool = False):
        self.is_running    = is_running
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

    def stop(self) -> None:
        """処理の中断を要求する"""
        self._stop_event.set()
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] 🛑 ユーザーにより停止命令が出されました。")

    def should_stop(self) -> bool:
        """中断命令が出ているか確認する"""
        return self._stop_event.is_set()

    def update(
        self,
        message: str,
        sub_message: str = "",
        step: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        # 進行状況が同じメッセージでログを埋め尽くさないようガード
        display_msg = message
        full_msg = f"{display_msg}: {sub_message}" if sub_message else display_msg
        
        # 前後の空白を除去して比較することで、重複ログを抑制
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


# ==========================================
# BackgroundReporter（ProgressStateを更新するレポーター）
# ==========================================
class BackgroundReporter:
    """バックグラウンドスレッドから ProgressState を更新する"""

    def __init__(self, state: ProgressState):
        self.state = state

    def report(self, message: str, level: str = "info") -> None:
        if self.state.should_stop():
            return
        prefix = "⚠️ " if level == "warning" else "🚨 " if level == "error" else "ℹ️ "
        self.state.update(f"{prefix}{message}")

    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None:
        if self.state.should_stop():
            return
        self.state.update(text, sub_message=sub_text, step=current, total=total)

    def update_streaming_text(self, text: str) -> None:
        if self.state.should_stop():
            return
        self.state.streaming_text = text


# ==========================================
# run_in_background（非同期タスクをスレッドで実行）
# ==========================================
def run_in_background(func: Callable, **kwargs) -> ProgressState:
    """
    非同期関数を別スレッドで実行し、UIにはProgressStateで進捗を公開する。
    UIスレッドをブロックせずにロングタスクを実行するために使用する。
    """
    state    = ProgressState(is_running=True)
    reporter = BackgroundReporter(state)

    def _target():
        try:
            # スレッド再利用時に備え、以前のループの残骸を完全に絶縁
            try:
                asyncio.set_event_loop(None)
            except:
                pass
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # 引数から reporter を二重に渡さないよう整理
            clean_kwargs = {k: v for k, v in kwargs.items() if k != "reporter"}
            result            = loop.run_until_complete(func(**clean_kwargs, reporter=reporter))
            state.result_data = result
            state.update("完了しました", step=state.total_steps)
        except Exception as e:
            state.error = str(e)
            logger.exception("Background task failed")
        finally:
            state.is_running = False
            if 'loop' in locals() and loop:
                try:
                    if not loop.is_closed():
                        # 未完了タスクのクリーンアップ
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        
                        if pending:
                            # キャンセル処理の完了を待機（タイムアウト付き）
                            loop.run_until_complete(asyncio.wait(pending, timeout=2.0))
                        
                        if loop.is_running():
                            loop.stop()
                        
                        # 完全に停止してから閉じる
                        loop.run_until_complete(loop.shutdown_asyncgens())
                        loop.close()
                except Exception:
                    pass
            asyncio.set_event_loop(None)

    thread = threading.Thread(target=_target, daemon=True)
    add_script_run_ctx(thread)
    thread.start()
    return state


# ==========================================
# TokenUsageTracker（トークン使用量追跡）
# ==========================================
def estimate_tokens(text: str) -> int:
    """Geminiのマルチリンガル・トークナイザーを意識した推定"""
    if not text: return 0
    # 日本語・記号: Gemini 1.5シリーズは約0.6〜0.8トークン/文字。0.7で計算。
    ja_chars = len(__import__("re").findall(r'[^\x00-\x7F]', text))
    # 英数字: 約1.3トークン/単語
    en_words = len(__import__("re").findall(r'\w+', text))
    return int(ja_chars * 0.7 + en_words * 1.3)


class TokenUsageTracker:
    def __init__(self, stats_dict: dict):
        self.stats = stats_dict

    def add_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.stats["prompt"]     += prompt_tokens
        self.stats["completion"] += completion_tokens
        self.stats["calls"]      += 1

    def get_cost_usd(self) -> float:
        return (self.stats["prompt"] * COST_INPUT_FLASH) + (self.stats["completion"] * COST_OUTPUT_FLASH)

    def get_summary(self) -> str:
        return (
            f"API呼び出し: {self.stats['calls']}回 | "
            f"推定コスト: ${self.get_cost_usd():.4f}"
        )

    def display_cost_estimate(self, text: str, label: str = "内容") -> None:
        """Streamlit上にトークン数と推定コストをキャプション表示する"""
        try:
            import streamlit as st
            tokens = estimate_tokens(text)
            # 入出力の比率が不明なため、Flashの中間レートで概算
            avg_rate = (COST_INPUT_FLASH + COST_OUTPUT_FLASH) / 2
            cost   = tokens * avg_rate
            st.caption(f"{label} 推定トークン: {tokens} (概算コスト: ${cost:.6f})")
        except Exception:
            pass
