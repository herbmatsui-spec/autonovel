"""
streamlit_app/stores/job_store.py — ジョブ(バックグラウンドタスク)の状態管理。

責務:
- 監視対象ジョブ(monitored_jobs)の取得・更新
- アクティブジョブ(set/clear)と関連一時状態の管理
- フラグメントバージョン管理(Reactive Update 用)
- 処理ロック(is_processing)の管理
"""
from __future__ import annotations

from typing import Any

from streamlit_app.stores.base import BaseStore


class JobStore(BaseStore):
    """ジョブ関連の状態アクセスをカプセル化するストア。"""

    @staticmethod
    def get_monitored_jobs() -> dict:
        """監視対象ジョブの辞書を取得"""
        return JobStore.get_runtime().monitored_jobs

    @staticmethod
    def set_active_job(job: Any, run_key: str = "default") -> None:
        """
        指定された run_key に対してアクティブなジョブをセットする。
        これにより、複数の独立したワークフロー（例: プロット生成と本文執筆）の並行監視が可能になる。
        """
        if job is None:
            JobStore.clear_active_job(run_key)
            return

        job_id = getattr(job, "task_id", None)
        JobStore.set_job_id(run_key, job_id)

        runtime = JobStore.get_runtime()
        current_monitored = runtime.monitored_jobs.copy()
        current_monitored[run_key] = job
        JobStore.update_runtime("monitored_jobs", current_monitored)

        JobStore._notify(f"active_job_{run_key}", job)

    @staticmethod
    def clear_active_job(run_key: str = "default") -> None:
        """指定された run_key のアクティブジョブと関連する一時状態をクリアする"""
        JobStore.clear_job_id(run_key)

        runtime = JobStore.get_runtime()
        if "monitored_jobs" in runtime.model_fields and run_key in runtime.monitored_jobs:
            current_monitored = runtime.monitored_jobs.copy()
            current_monitored[run_key] = None
            JobStore.update_runtime("monitored_jobs", current_monitored)

        # ポーリング制御変数のクリーンアップ
        if run_key in runtime.poll_fail_count:
            current_fail = runtime.poll_fail_count.copy()
            current_fail[run_key] = 0
            JobStore.update_runtime("poll_fail_count", current_fail)
        if run_key in runtime.poll_skip_until:
            current_skip = runtime.poll_skip_until.copy()
            current_skip[run_key] = 0.0
            JobStore.update_runtime("poll_skip_until", current_skip)

        JobStore._notify(f"active_job_{run_key}", None)

    @staticmethod
    def bump_fragment_version(part: str) -> None:
        """特定のUIパーツのバージョンを上げ、フラグメントに更新を通知する"""
        runtime = JobStore.get_runtime()
        versions = runtime.fragment_versions.copy()
        versions[part] = versions.get(part, 0) + 1
        JobStore.update_runtime("fragment_versions", versions)

    @staticmethod
    def get_fragment_version(part: str) -> int:
        """フラグメントの現在のバージョンを取得"""
        return JobStore.get_runtime().fragment_versions.get(part, 0)

    @staticmethod
    def set_job_id(run_key: str, job_id: str | None) -> None:
        """RuntimeState の active_job_ids 辞書を更新する"""
        runtime = JobStore.get_runtime()
        current = runtime.active_job_ids.copy()
        current[run_key] = job_id
        JobStore.update_runtime("active_job_ids", current)

    @staticmethod
    def clear_job_id(run_key: str) -> None:
        """RuntimeState の active_job_ids から指定されたキーを削除またはNoneにする"""
        runtime = JobStore.get_runtime()
        if hasattr(runtime, "active_job_ids") and run_key in runtime.active_job_ids:
            current = runtime.active_job_ids.copy()
            current[run_key] = None
            JobStore.update_runtime("active_job_ids", current)

    @staticmethod
    def set_processing_lock(locked: bool) -> None:
        """ジョブ起動時などの不安定な期間にポーリングを抑制するためのロック"""
        JobStore.update_runtime("ui_processing_lock", locked)

    @staticmethod
    def is_processing() -> bool:
        """ロック状態を確認する"""
        return JobStore.get_runtime().ui_processing_lock
