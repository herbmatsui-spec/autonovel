"""
progress.py - バックグラウンドタスクの進捗監視および状態管理用プロキシ
"""
from __future__ import annotations

import logging
import time
from typing import Any

from src.infrastructure.api import api_client
from streamlit_app.workflow_types import WORKFLOW_API_MAP, WorkflowType

logger = logging.getLogger(__name__)


class ProgressStateProxy:
    """バックグラウンドタスクの進捗状態をAPI経由で監視・保持するプロキシクラス"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.trace_id: str = "N/A"
        self._last_api_tokens = {"prompt": 0, "completion": 0, "calls": 0}
        self.is_running: bool = False
        self.current_step: int = 0
        self.total_steps: int = 0
        self.message: str = "初期化中..."
        self.sub_message: str = ""
        self.streaming_text: str = ""
        self.logs: list[str] = []
        self.error: str | None = None
        self.result_data: Any = None
        self.token_usage = {"prompt": 0, "completion": 0, "calls": 0}
        self.start_time: float = time.time()
        self.refresh()

    def _get_snapshot(self) -> dict[str, Any]:
        """状態変更検知用のスナップショットを作成"""
        return {
            "is_running": self.is_running,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "message": self.message,
            "sub_message": self.sub_message,
            "streaming_text": self.streaming_text,
            "logs_len": len(self.logs),
            "error": self.error,
            "result_data": self.result_data
        }

    def refresh(self, timeout: float = 5.0) -> bool:
        """
        最新の状態をAPIから取得し、内部状態を更新する。
        状態に変更があった場合は True を返し、変更がなかった場合は False を返す。
        """
        if not self.task_id or self.task_id == "unknown":
            self.error = f"タスクの初期化に失敗しました。バックエンドAPIサーバー（{api_client.API_BASE_URL}）に接続できません。"
            return False

        data = api_client.get_task_status(self.task_id, timeout=timeout)
        old_state = self._get_snapshot()

        self.is_running = data.get("is_running", False)
        self.current_step = data.get("current_step", 0)
        self.total_steps = data.get("total_steps", 0)
        self.message = data.get("message", "準備中...")
        self.sub_message = data.get("sub_message", "")
        self.trace_id = data.get("trace_id", "N/A")
        self.streaming_text = data.get("streaming_text", "")
        self.logs = data.get("logs", [])
        self.error = data.get("error")
        self.result_data = data.get("result_data")

        raw_usage = data.get("token_usage", {"prompt": 0, "completion": 0, "calls": 0})
        # 前回との差分（今回の増分）のみを記録
        incremental_usage = {
            "prompt": max(0, raw_usage.get("prompt", 0) - self._last_api_tokens.get("prompt", 0)),
            "completion": max(0, raw_usage.get("completion", 0) - self._last_api_tokens.get("completion", 0)),
            "calls": max(0, raw_usage.get("calls", 0) - self._last_api_tokens.get("calls", 0))
        }
        self.token_usage = incremental_usage
        self._last_api_tokens = raw_usage
        self.start_time = data.get("start_time", time.time())

        return old_state != self._get_snapshot()

    def stop(self) -> None:
        """実行中のタスクを停止する"""
        api_client.stop_task(self.task_id)

    @property
    def status(self) -> str:
        """後方互換性のためのステータスプロパティ"""
        if self.is_running:
            return "RUNNING"
        elif self.error:
            return "FAILED"
        else:
            return "SUCCESS"

    @property
    def result(self) -> Any:
        """後方互換性のための結果データプロパティ"""
        return self.result_data

    @property
    def error_message(self) -> str | None:
        """後方互換性のためのエラーメッセージプロパティ"""
        return self.error


def _prepare_api_kwargs(arg_names: list[str], all_kwargs: dict[str, Any]) -> dict[str, Any]:
    """API呼び出しに必要な引数だけを抽出するヘルパー"""
    api_kwargs = {name: all_kwargs.get(name) for name in arg_names}
    # configとapi_keyは共通で渡す
    api_kwargs.update({"api_key": all_kwargs.get("api_key"), "config": all_kwargs.get("config")})
    return api_kwargs


def run_in_background(workflow_type: WorkflowType, **kwargs) -> ProgressStateProxy:
    """
    バックグラウンドワークフローを動的に解決して実行する。
    """
    from streamlit_app.state import UIStateStore, get_session

    # セッション状態から共通パラメータを取得
    session = get_session()
    api_key = session.api_key

    # session.config (NSFW/官能設定等) に、サイドバーで選択された
    # グローバル設定 (config_data: モデル選択・OpenRouter設定等) をマージして送信する。
    # これにより、バックエンドワーカーがプロセスキャッシュに関係なく
    # 最新のモデル選択を確実に反映できる。
    config = dict(session.config or {})
    try:
        runtime_cfg = UIStateStore.get_runtime().config_data or {}
        for key, value in runtime_cfg.items():
            # session.config 側で明示的に設定済みの値は上書きしない
            config.setdefault(key, value)
    except Exception:
        pass

    kwargs.update({"api_key": api_key, "config": config})

    try:
        if workflow_type in WORKFLOW_API_MAP:
            api_method_name, arg_names = WORKFLOW_API_MAP[workflow_type]
            api_func = getattr(api_client, api_method_name)

            # APIに必要な引数だけを抽出して呼び出し
            api_kwargs = _prepare_api_kwargs(arg_names, kwargs)
            task_id = api_func(**api_kwargs)
        else:
            logger.error(f"Unknown background workflow type: {workflow_type}")
            task_id = "unknown"

        return ProgressStateProxy(task_id)
    except Exception as e:
        logger.exception(f"Error launching background task {workflow_type}: {e}")
        proxy = ProgressStateProxy("unknown")
        proxy.error = f"タスク起動エラー: {str(e)}"
        return proxy
