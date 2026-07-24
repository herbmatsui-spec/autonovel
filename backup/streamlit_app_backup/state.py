"""
streamlit_app/state.py — Streamlit セッション状態の型安全な管理
"""
from __future__ import annotations

from typing import Any, Optional

import streamlit as st
from pydantic import BaseModel, Field

from schemas.app_state import AppStateModel
from src.models.emotional_hook import EmotionalHookSpec

# -----------------------------------------------------------------------------
# 型定義
# -----------------------------------------------------------------------------


class WizardState(BaseModel):
    """ウィザード形式の入力状態を管理するモデル"""

    step: int = 1
    data: dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = False


class UIState(BaseModel):
    """
    UI層の非永続的な状態（フォーム入力、UIフラグ、一時的な選択状態など）を管理するモデル。
    AppStateModel に含めると永続化コストが高くなる一時的な状態をここに集約する。
    """

    # フォーム状態
    form_data: dict[str, Any] = Field(default_factory=dict)

    # UI表示フラグ
    show_modal: bool = False
    active_tab: str = "home"

    # 選択状態
    selected_item_id: Optional[str] = None
    current_book_id: Optional[int] = None

    # 生成履歴
    generation_history: list[dict[str, Any]] = Field(default_factory=list)

    # 執筆進捗
    active_task_id: Optional[str] = None
    writing_progress: dict[str, Any] = Field(
        default_factory=lambda: {
            "current_ep": 0,
            "total": 0,
            "status": "idle",
        }
    )

    # 検索/フィルタ
    search_query: str = ""
    filter_settings: dict[str, Any] = Field(default_factory=dict)


# Note: AppStateModel is now defined in schemas/app_state.py to avoid circular imports
# and to centralize the schema definition.

# -----------------------------------------------------------------------------
# セッションアクセサ
# -----------------------------------------------------------------------------


class SessionManager:
    """
    UIStateStore / AppStateModel と st.session_state の同期、および永続化を管理するクラス。
    「st.session_state への唯一の正当なアクセスポイント」として機能する。
    UIコンポーネントは SessionManager や st.session_state に直接アクセスせず、
    UIStateStore を介して状態を読み書きすること。
    """

    from streamlit_app.state_keys import APP_STATE_KEY

    _STATE_KEY = APP_STATE_KEY

    @classmethod
    def _get_storage_path(cls):
        """セッション固有の保存パスを生成する"""
        from pathlib import Path

        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx

            ctx = get_script_run_ctx()
            session_id = ctx.session_id if ctx else "default"
        except Exception:
            session_id = "default"
        return Path("storage") / f"session_{session_id}.json"

    @classmethod
    def get_state(cls) -> AppStateModel:
        """
        セッション状態から AppStateModel を取得する。
        存在しない場合はファイルから復元し、なければ初期化して保存する。
        """
        if cls._STATE_KEY not in st.session_state:
            # 1. ファイルから復元を試みる
            state = cls._load_from_disk()
            if state is None:
                state = AppStateModel()
            st.session_state[cls._STATE_KEY] = state

        return st.session_state[cls._STATE_KEY]

    @classmethod
    def save_state(cls, state: AppStateModel) -> None:
        """モデルをセッション状態に書き戻し、ディスクに永続化する"""
        st.session_state[cls._STATE_KEY] = state
        cls._save_to_disk(state)

    @classmethod
    def _save_to_disk(cls, state: AppStateModel) -> None:
        """状態を JSON ファイルとして保存する"""
        try:
            save_path = cls._get_storage_path()
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                # PydanticモデルをJSON文字列として保存 (active_jobはシリアライズ不能なプロキシのため除外)
                f.write(state.model_dump_json(indent=2, exclude={"active_job"}))
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Session state save failed: {e}")

    @classmethod
    def _load_from_disk(cls) -> AppStateModel | None:
        """JSON ファイルから状態を復元する"""
        try:
            save_path = cls._get_storage_path()
            if save_path.exists():
                with open(save_path, "r", encoding="utf-8") as f:
                    data = f.read()
                    return AppStateModel.model_validate_json(data)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Session state load failed: {e}")
        return None

    @classmethod
    def reset(cls) -> None:
        """状態をリセットする"""
        if cls._STATE_KEY in st.session_state:
            del st.session_state[cls._STATE_KEY]

    @classmethod
    def migrate_from_session(cls, key: str, default: Any = None) -> Any:
        """st.session_state から値を取得してUIStateStoreに移行"""
        if key in st.session_state:
            value = st.session_state[key]
            del st.session_state[key]
            ui_state = st.session_state.get("ui_state")
            if ui_state is not None and hasattr(ui_state, "form_data"):
                ui_state.form_data[key] = value
            return value
        return default


# 便利なショートカット関数
def get_session() -> AppStateModel:
    return SessionManager.get_state()


DESIRE_TO_HOOK_MAP = {
    "カタルシス": "catharsis",
    "共感の最深": "empathy_peak",
    "背筋の寒さ": "chilling",
    "義憤": "righteous_anger",
    " Triumph ": "triumph",
    "静寂の喜び": "serenity",
    "郷愁": "nostalgia",
    "畏敬": "awe",
}


def desires_to_hook(desires: list[str]) -> Optional["EmotionalHookSpec"]:
    """
    selected_desires の先頭を感情起点名に変換し、EmotionalHookSpec を構築する。

    desires が空なら None を返す。
    """
    if not desires:
        return None
    first = desires[0]
    hook_name = DESIRE_TO_HOOK_MAP.get(first)
    if hook_name is None:
        return None
    return EmotionalHookSpec(
        hook_name=hook_name,
        one_line_intent=first,
    )


# -----------------------------------------------------------------------------
# 状態管理クラスの分離 (Single Responsibility Principle)
# -----------------------------------------------------------------------------
# UIStateStore は 475 行・40 以上の静的メソッドを持ち SRP に反していたため、
# 責務を JobStore / SessionStore / PollStateStore / ToastStore へ分割した。
# 現在は合成パターンを採用し、各ストアのインスタンスを保持する。
from streamlit_app.stores import (  # noqa: E402
    BaseStore,
    JobStore,
    PollStateStore,
    SessionStore,
    ToastStore,
)


class UIStateStore:
    """UI state store implementation using composition pattern."""

    def __init__(self):
        self._job_store = JobStore()
        self._poll_store = PollStateStore()
        self._toast_store = ToastStore()
        self._session_store = SessionStore()

    _subscribers = BaseStore._subscribers

    @staticmethod
    def get_runtime():
        return SessionStore.get_runtime()

    @staticmethod
    def get_runtime_state():
        return SessionStore.get_runtime()

    # Delegate to JobStore
    @staticmethod
    def get_monitored_jobs():
        return JobStore.get_monitored_jobs()

    @staticmethod
    def set_active_job(job, run_key="default"):
        return JobStore.set_active_job(job, run_key)

    @staticmethod
    def clear_active_job(run_key="default"):
        return JobStore.clear_active_job(run_key)

    @staticmethod
    def bump_fragment_version(part):
        return JobStore.bump_fragment_version(part)

    @staticmethod
    def get_fragment_version(part):
        return JobStore.get_fragment_version(part)

    @staticmethod
    def set_job_id(run_key, job_id):
        return JobStore.set_job_id(run_key, job_id)

    @staticmethod
    def clear_job_id(run_key):
        return JobStore.clear_job_id(run_key)

    @staticmethod
    def set_processing_lock(locked):
        return JobStore.set_processing_lock(locked)

    @staticmethod
    def is_processing():
        return JobStore.is_processing()

    # Delegate to PollStateStore
    @staticmethod
    def get_poll_fail_count(run_key):
        return PollStateStore.get_poll_fail_count(run_key)

    @staticmethod
    def increment_poll_fail_count(run_key):
        return PollStateStore.increment_poll_fail_count(run_key)

    @staticmethod
    def reset_poll_fail_count(run_key):
        return PollStateStore.reset_poll_fail_count(run_key)

    @staticmethod
    def get_poll_skip_until(run_key):
        return PollStateStore.get_poll_skip_until(run_key)

    @staticmethod
    def set_poll_skip_until(run_key, timestamp):
        return PollStateStore.set_poll_skip_until(run_key, timestamp)

    @staticmethod
    def set_save_status(ep_num, status):
        return PollStateStore.set_save_status(ep_num, status)

    @staticmethod
    def get_save_status(ep_num):
        return PollStateStore.get_save_status(ep_num)

    # Delegate to ToastStore
    @staticmethod
    def is_toast_notified(key):
        return ToastStore.is_toast_notified(key)

    @staticmethod
    def mark_toast_notified(key):
        return ToastStore.mark_toast_notified(key)

    @staticmethod
    def clear_toast_notified(key):
        return ToastStore.clear_toast_notified(key)

    @staticmethod
    def toast_notify(key, message, icon=None):
        return ToastStore.toast_notify(key, message, icon)

    # Delegate to SessionStore
    @staticmethod
    def set_wizard_step(step):
        return SessionStore.set_wizard_step(step)

    @staticmethod
    def update_wizard_data(data):
        return SessionStore.update_wizard_data(data)

    @staticmethod
    def set_easy_genre(genre_key):
        return SessionStore.set_easy_genre(genre_key)

    @staticmethod
    def get_api_key_validation_state():
        return SessionStore.get_api_key_validation_state()

    @staticmethod
    def set_api_key_validation_state(state):
        return SessionStore.set_api_key_validation_state(state)

    @staticmethod
    def get_api_key_validation_key():
        return SessionStore.get_api_key_validation_key()

    @staticmethod
    def set_api_key_validation_key(key):
        return SessionStore.set_api_key_validation_key(key)

    @staticmethod
    def get_api_key_validation_error():
        return SessionStore.get_api_key_validation_error()

    @staticmethod
    def set_api_key_validation_error(msg):
        return SessionStore.set_api_key_validation_error(msg)

    @staticmethod
    def reset_api_key_validation():
        return SessionStore.reset_api_key_validation()

    @staticmethod
    def get_api_key_input():
        return SessionStore.get_api_key_input()

    @staticmethod
    def set_api_key_input(value):
        return SessionStore.set_api_key_input(value)

    # Delegate to BaseStore
    @staticmethod
    def get():
        return BaseStore.get()

    @staticmethod
    def get_runtime():
        return BaseStore.get_runtime()

    @staticmethod
    def update(update_func, notify_keys=None):
        return BaseStore.update(update_func, notify_keys)

    @staticmethod
    def update_runtime(key, value, notify=True):
        return BaseStore.update_runtime(key, value, notify)

    @staticmethod
    def subscribe(key, callback):
        return BaseStore.subscribe(key, callback)

    @staticmethod
    def _notify(key, value):
        return BaseStore._notify(key, value)

    @staticmethod
    def get_rerun_count():
        return BaseStore.get_rerun_count()

    @staticmethod
    def increment_rerun_count():
        return BaseStore.increment_rerun_count()

    @staticmethod
    def get_book_plots(book_id):
        return BaseStore.get_book_plots(book_id)

    @property
    def ui_state(self) -> UIState:
        """
        UI state getter.
        存在しない場合は初期化して返す。
        """
        from streamlit_app.state_keys import UI_STATE_KEY

        if UI_STATE_KEY not in st.session_state:
            st.session_state[UI_STATE_KEY] = UIState()
        return st.session_state[UI_STATE_KEY]

    def update_ui_state(self, **kwargs) -> None:
        """
        UI状態を更新する。キーワード引数で指定されたフィールドのみを更新する。
        """
        state = self.ui_state
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                state.form_data[key] = value
            self._notify(key, value)

    def get_ui_state_value(self, key: str, default: Any = None) -> Any:
        """
        UI状態から値を取得する。
        明示的なフィールドまたは form_data のいずれかから値を返す。
        """
        state = self.ui_state
        if hasattr(state, key):
            return getattr(state, key)
        return state.form_data.get(key, default)

    def reset_ui_state(self) -> None:
        """
        UI状態をデフォルト値にリセットする。
        """
        from streamlit_app.state_keys import UI_STATE_KEY

        st.session_state[UI_STATE_KEY] = UIState()

    def set_form_data(self, key: str, value: Any) -> None:
        """
        フォームデータを設定する。
        """
        state = self.ui_state
        state.form_data[key] = value

    def get_form_data(self, key: str, default: Any = None) -> Any:
        """
        フォームデータを取得する。
        """
        state = self.ui_state
        return state.form_data.get(key, default)

    def set_modal_visible(self, visible: bool) -> None:
        """
        モーダル表示フラグを設定する。
        """
        self.update_ui_state(show_modal=visible)

    def is_modal_visible(self) -> bool:
        """
        モーダル表示フラグを取得する。
        """
        return self.get_ui_state_value("show_modal", False)
