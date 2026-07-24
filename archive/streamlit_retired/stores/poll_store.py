"""
streamlit_app/stores/poll_store.py — ポーリングとタスク進捗の状態管理。

責務:
- ポーリング失敗回数(poll_fail_count)の取得・増減・リセット
- ポーリングスキップ期限(poll_skip_until)の取得・設定
- エピソードごとの保存状態(save_status)の管理
"""
from __future__ import annotations

from streamlit_app.stores.base import BaseStore


class PollStateStore(BaseStore):
    """ポーリングとタスク進捗関連の状態アクセスをカプセル化するストア。"""

    @staticmethod
    def get_poll_fail_count(run_key: str) -> int:
        """ポーリング失敗回数を取得"""
        return PollStateStore.get_runtime().poll_fail_count.get(run_key, 0)

    @staticmethod
    def increment_poll_fail_count(run_key: str) -> None:
        """ポーリング失敗回数をインクリメント"""
        runtime = PollStateStore.get_runtime()
        current = runtime.poll_fail_count.copy()
        current[run_key] = current.get(run_key, 0) + 1
        PollStateStore.update_runtime("poll_fail_count", current)

    @staticmethod
    def reset_poll_fail_count(run_key: str) -> None:
        """ポーリング失敗回数をリセット"""
        runtime = PollStateStore.get_runtime()
        current = runtime.poll_fail_count.copy()
        current[run_key] = 0
        PollStateStore.update_runtime("poll_fail_count", current)

    @staticmethod
    def get_poll_skip_until(run_key: str) -> float:
        """ポーリングスキップまでのタイムスタンプを取得"""
        return PollStateStore.get_runtime().poll_skip_until.get(run_key, 0.0)

    @staticmethod
    def set_poll_skip_until(run_key: str, timestamp: float) -> None:
        """ポーリングスキップまでのタイムスタンプを設定"""
        runtime = PollStateStore.get_runtime()
        current = runtime.poll_skip_until.copy()
        current[run_key] = timestamp
        PollStateStore.update_runtime("poll_skip_until", current)

    @staticmethod
    def set_save_status(ep_num: int, status: str) -> None:
        """エピソードごとの保存状態をセットする（status: 'saving', 'saved', 'idle'）"""
        runtime = PollStateStore.get_runtime()
        current = runtime.save_status.copy()
        current[ep_num] = status
        PollStateStore.update_runtime("save_status", current)
        PollStateStore._notify(f"save_status_{ep_num}", status)

    @staticmethod
    def get_save_status(ep_num: int) -> str:
        """エピソードの現在の保存状態を取得する"""
        return PollStateStore.get_runtime().save_status.get(ep_num, "idle")
