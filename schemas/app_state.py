from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WizardState(BaseModel):
    """ウィザード形式の入力状態を管理するモデル"""
    step: int = 1
    data: dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = False

class TokenStats(BaseModel):
    """APIトークン使用量統計"""
    prompt: int = 0
    completion: int = 0
    calls: int = 0

class AppRuntimeState(BaseModel):
    """
    UI層で利用される非永続的なランタイム状態。
    UIStateStore.get_runtime_value でアクセスされていたものを構造化する。
    """
    app_mode: str = "easy"
    llm_provider: str = "gemini"
    is_api_key_valid: bool = False
    forbidden_patterns: list[str] = Field(default_factory=list)
    selected_desires: list[str] = Field(default_factory=lambda: ["カタルシス"])
    selected_emotional_hook: str | None = Field(default=None, description="選択中の感情起点名")
    backend_connection_error: bool = False
    token_stats: TokenStats = Field(default_factory=TokenStats)
    active_job_ids: dict[str, str | None] = Field(default_factory=dict)
    last_passion: float = 0.6
    last_word_count: int = 2500
    easy_genre_key: str | None = None
    download_zip_path: str | None = None
    download_zip_name: str | None = None
    download_zip_data: bytes | None = None
    # UI一時状態
    rerun_count: int = 0
    api_key_input: str = ""
    ui_processing_lock: bool = False
    save_status: dict[int, str] = Field(default_factory=dict)
    monitored_jobs: dict[str, Any] = Field(default_factory=dict)
    poll_fail_count: dict[str, int] = Field(default_factory=dict)
    poll_skip_until: dict[str, float] = Field(default_factory=dict)
    # フラグメントごとのバージョン管理 (Reactive Update 用)
    fragment_versions: dict[str, int] = Field(default_factory=lambda: {"status": 0, "logs": 0, "usage": 0})
    # === st.session_state 置き換え用 新規フィールド ===
    # api_key_future のシリアライズ可能な状態
    # "idle" / "pending" / "valid" / "invalid" / "error"
    api_key_validation_state: str = "idle"
    # 最後に検証したAPIキー値
    api_key_validation_key: str = ""
    # 検証エラーメッセージ
    api_key_validation_error: str = ""
    # toast 重複防止キー
    toasted_notification_keys: list[str] = Field(default_factory=list)
    # 設定データキャッシュ (config/streamlit_adapter の st.session_state.config 置き換え)
    config_data: dict[str, Any] = Field(default_factory=dict)

class AppStateModel(BaseModel):
    """
    アプリケーション全体のセッション状態を定義するルートモデル。
    """
    # 認証・基本設定
    api_key: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    # 現在の操作対象
    current_book_id: str | None = None
    selected_episode_id: str | None = None

    # 各種ウィザード状態
    wizard: WizardState = Field(default_factory=WizardState)

    # バックグラウンドタスク状態
    active_job: Any | None = None

    # 履歴・キャッシュ
    last_action_timestamp: float | None = None
    error_message: str | None = None

    # UI-specific runtime state
    runtime: AppRuntimeState = Field(default_factory=AppRuntimeState)

    model_config = {
        "arbitrary_types_allowed": True,
        "protected_namespaces": ()
    }

