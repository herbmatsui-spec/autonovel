"""
streamlit_app/stores/base.py — 全ストアの共通基底。

st.session_state / AppStateModel への型安全なアクセス、変更通知(subscribe)、
および更新ヘルパ(update / update_runtime) を提供する。
各機能ストア(JobStore 等)はこのクラスを継承して固有の責務のみを持つ。
"""
from __future__ import annotations

from typing import Any, Callable

from schemas.app_state import AppRuntimeState, AppStateModel
from streamlit_app.state import SessionManager, get_session


class BaseStore:
    """
    状態アクセスの共通基盤。
    サブクラスはこのクラスを継承し、機能別のメソッドのみを定義する。
    """

    _subscribers: dict[str, list[Callable[[Any], None]]] = {}

    # ==========================================================================
    # Core State Access
    # ==========================================================================
    @staticmethod
    def get() -> AppStateModel:
        return get_session()

    @staticmethod
    def get_runtime() -> AppRuntimeState:
        """型安全なランタイム状態へのアクセスを提供"""
        return get_session().runtime

    @staticmethod
    def get_runtime_state() -> AppRuntimeState:
        """[DEPRECATED] UIStateStore.get_runtime() を使用してください。"""
        import warnings
        warnings.warn(
            "BaseStore.get_runtime_state is deprecated. Use BaseStore.get_runtime() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return get_session().runtime

    @staticmethod
    def update(update_func: Callable[[AppStateModel], None], notify_keys: list[str] | None = None) -> None:
        """
        状態を安全に更新し、保存する。
        update_func は AppStateModel を受け取り、変更を加える関数であること。
        notify_keys を指定した場合、更新後にそれらのキーに対応する通知を飛ばす。
        """
        BaseStore.increment_rerun_count()
        state = get_session()
        update_func(state)
        SessionManager.save_state(state)

        if notify_keys:
            for key in notify_keys:
                val = getattr(state, key, getattr(state.runtime, key, None))
                BaseStore._notify(key, val)

    @staticmethod
    def update_runtime(key: str, value: Any, notify: bool = True) -> None:
        """
        ランタイム状態の特定の属性を更新し、状態を保存する。
        """
        state = get_session()
        if hasattr(state.runtime, key):
            setattr(state.runtime, key, value)
        else:
            raise AttributeError(f"AppRuntimeState has no attribute '{key}'")
        SessionManager.save_state(state)
        if notify:
            BaseStore._notify(key, value)

    @staticmethod
    def persist() -> None:
        """現在の状態をディスクに永続化する（明示的呼び出し用）"""
        SessionManager.save_state(get_session())

    @staticmethod
    def subscribe(key: str, callback: Callable[[Any], None]) -> None:
        """特定のキーの値が変更されたときに呼び出されるコールバックを登録する"""
        if key not in BaseStore._subscribers:
            BaseStore._subscribers[key] = []
        BaseStore._subscribers[key].append(callback)

    @staticmethod
    def _notify(key: str, value: Any) -> None:
        """登録されたコールバックをすべて実行する"""
        for callback in BaseStore._subscribers.get(key, []):
            try:
                callback(value)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"State change callback failed for {key}: {e}")

    @staticmethod
    def get_book_plots(book_id: int) -> list[Any]:
        """UI層が直接Engineにアクセスせず、EngineService経由でプロットデータを取得するためのメソッド。"""
        from src.engine_service import EngineService
        service = EngineService.get_instance()
        return service.get_book_plots(book_id)

    @staticmethod
    def get_runtime_value(key: str, default: Any = None) -> Any:
        """
        [DEPRECATED] UI実行時の一次的な状態を取得する。
        UIStateStore.get_runtime() を使用して属性にアクセスしてください。
        """
        import warnings
        warnings.warn(
            "BaseStore.get_runtime_value is deprecated and will be removed. "
            "Use BaseStore.get_runtime() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        state = get_session()
        return getattr(state.runtime, key, default)

    # ==========================================================================
    # Rerun Counter (core infra used by update())
    # ==========================================================================
    @staticmethod
    def get_rerun_count() -> int:
        """再描画回数を取得する"""
        return BaseStore.get_runtime().rerun_count

    @staticmethod
    def increment_rerun_count() -> None:
        """再描画回数をインクリメントする"""
        BaseStore.update_runtime("rerun_count", BaseStore.get_runtime().rerun_count + 1)
