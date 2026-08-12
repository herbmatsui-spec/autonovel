"""
かんたんモード用バックグラウンド実行ランナー
Streamlit UIから EasyModePipeline を非同期実行し、進捗を UI に反映
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.backend.background import BackgroundReporter, ProgressState
from src.easy_mode import EasyModePipeline, PipelineConfig
from streamlit_app.state import UIStateStore

logger = logging.getLogger(__name__)

# ログ保存ディレクトリ
LOG_DIR = Path("logs/easy_mode")
LOG_DIR.mkdir(parents=True, exist_ok=True)


class EasyModeRunner:
    """かんたんモード パイプラインのバックグラウンド実行管理"""

    def __init__(self, engine, genre: str, target_episodes: int = 8):
        self.engine = engine
        self.genre = genre
        self.target_episodes = target_episodes
        self.task_id = f"easy_{genre}_{int(time.time())}"
        self.progress_state: Optional[ProgressState] = None
        self.reporter: Optional[BackgroundReporter] = None
        self.pipeline: Optional[EasyModePipeline] = None
        self.result: Any = None
        self.error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._log_file = LOG_DIR / f"{self.task_id}.jsonl"
        
    def _persist_log(self, log_entry: dict) -> None:
        """ログをJSONL形式で永続化"""
        try:
            log_entry["timestamp"] = datetime.now().isoformat()
            log_entry["task_id"] = self.task_id
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist log: {e}")

    def start(self) -> None:
        """バックグラウンドスレッドで実行開始"""
        if self._thread and self._thread.is_alive():
            logger.warning("Runner already running")
            return

        self._stop_event.clear()
        self.progress_state = ProgressState(
            is_running=True,
            task_id=self.task_id,
            repo=None,
        )
        self.reporter = BackgroundReporter(self.progress_state)

        # 開始ログを永続化
        self._persist_log({"event": "start", "genre": self.genre, "target_episodes": self.target_episodes})

        # monitored_jobs に登録（UI のポーリング用）
        UIStateStore.set_active_job(self, run_key="easy_job")

        self._thread = threading.Thread(target=self._run_async, daemon=True)
        self._thread.start()
        logger.info(f"EasyModeRunner started: {self.task_id}")

    def _run_async(self) -> None:
        """非同期実行ラッパー"""
        try:
            asyncio.run(self._run_pipeline())
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            self.error = str(e)
            self._persist_log({"event": "error", "error": str(e)})
            if self.progress_state:
                self.progress_state.is_running = False
                self.progress_state.error = str(e)
                self.progress_state._save_to_db()
        finally:
            # 完了時にジョブをクリア
            UIStateStore.clear_active_job(run_key="easy_job")

    async def _run_pipeline(self) -> None:
        """パイプライン実行"""
        self.progress_state.update("初期化中", "パイプライン準備中...", step=0, total=4)

        config = PipelineConfig(
            genre=self.genre,
            target_episodes=self.target_episodes,
            max_rewrite_iterations=3,
            target_audit_score=95.0,
            enable_spice_guard=True,
            progress_callback=self._progress_callback,
        )

        self.pipeline = EasyModePipeline(self.engine, config)

        # 進捗コールバック付きで実行
        self.result = await self.pipeline.run()

        self.progress_state.is_running = False
        self.progress_state.message = "完了"
        self.progress_state.result_data = {
            "title": self.result.title,
            "concept": self.result.concept,
            "total_episodes": self.result.total_episodes,
            "total_words": sum(ep.word_count for ep in self.result.episodes),
            "average_audit_score": sum(ep.audit_score for ep in self.result.episodes) / len(self.result.episodes) if self.result.episodes else 0,
            "genre": self.result.genre,
        }
        self.progress_state._save_to_db()
        
        # 完了ログを永続化
        self._persist_log({
            "event": "complete",
            "title": self.result.title,
            "total_episodes": self.result.total_episodes,
            "total_words": sum(ep.word_count for ep in self.result.episodes),
            "average_audit_score": sum(ep.audit_score for ep in self.result.episodes) / len(self.result.episodes) if self.result.episodes else 0,
            "needs_human_review_count": sum(1 for ep in self.result.episodes if getattr(ep, 'needs_human_review', False))
        })
        logger.info(f"Pipeline completed: {self.task_id}")

    def _progress_callback(self, stage: str, current: int, total: int) -> None:
        """進捗コールバック（パイプラインから呼ばれる）"""
        if self._stop_event.is_set() or (self.progress_state and self.progress_state.should_stop()):
            self._stop_event.set()
            raise RuntimeError("Cancelled by user")

        if not self.progress_state:
            return

        stage_messages = {
            "bible": ("📖 Bible生成中", f"ジャンル設定反映中... ({current}/{total})"),
            "plot": ("📝 プロット生成中", f"全{total}話の構成作成中... ({current}/{total})"),
            "writing": ("✍️ 本文執筆中", f"第{current}話を執筆中... ({current}/{total})"),
            "audit": ("⚖️ 監査・リライト中", f"第{current}話を品質チェック中..."),
            "episode_complete": ("✅ 話完了", f"第{current}話が完了 ({current}/{total})"),
            "finalizing": ("📦 完結処理中", "最終整理・メタデータ生成中..."),
        }

        msg, sub = stage_messages.get(stage, (stage, ""))
        step_map = {
            "bible": 1,
            "plot": 2,
            "writing": 3,
            "audit": 3,
            "finalizing": 4,
        }

        step = step_map.get(stage, current)
        self.progress_state.update(msg, sub_message=sub, step=step, total=4)

        # UI用ログも更新
        runtime = UIStateStore.get_runtime()
        runtime.easy_mode_step = stage
        runtime.easy_mode_current_episode = current
        runtime.easy_mode_total_episodes = total
        runtime.easy_mode_progress = min(100, int((step / 4) * 100))

        log_msg = f"[{time.strftime('%H:%M:%S')}] {msg}: {sub}"
        runtime.easy_mode_logs.append(log_msg)

        # fragment version bump for UI update
        UIStateStore.bump_fragment_version("status")

    def stop(self) -> None:
        """実行中断"""
        self._stop_event.set()
        if self.progress_state:
            self.progress_state.stop()
        logger.info(f"EasyModeRunner stop requested: {self.task_id}")

    # ProgressState 互換プロパティ（UI ポーリング用）
    @property
    def is_running(self) -> bool:
        return self.progress_state.is_running if self.progress_state else False

    @property
    def message(self) -> str:
        return self.progress_state.message if self.progress_state else "待機中"

    @property
    def sub_message(self) -> str:
        return self.progress_state.sub_message if self.progress_state else ""

    @property
    def current_step(self) -> int:
        return self.progress_state.current_step if self.progress_state else 0

    @property
    def total_steps(self) -> int:
        return self.progress_state.total_steps if self.progress_state else 4

    @property
    def logs(self) -> list:
        return self.progress_state.logs if self.progress_state else []

    @property
    def result_data(self) -> Any:
        return self.progress_state.result_data if self.progress_state else None

    @property
    def error(self) -> Optional[str]:
        return self.progress_state.error if self.progress_state else self._error

    @error.setter
    def error(self, value: Optional[str]):
        self._error = value
        if self.progress_state:
            self.progress_state.error = value

    @property
    def start_time(self) -> float:
        return self.progress_state.start_time if self.progress_state else time.time()

    def refresh(self, timeout: float = 5.0) -> bool:
        """UI ポーリング用（ProgressState 互換）"""
        # 状態変更があれば True を返す
        return True


def start_easy_mode_generation(engine, genre: str, target_episodes: int = 8) -> EasyModeRunner:
    """かんたんモード生成を開始するエントリーポイント"""
    runner = EasyModeRunner(engine, genre, target_episodes)
    runner.start()
    return runner
