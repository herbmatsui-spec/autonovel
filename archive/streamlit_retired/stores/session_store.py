"""
streamlit_app/stores/session_store.py — セッション/ランタイム設定の状態管理。

責務:
- ウィザード・ジャンル設定(set_wizard_step / update_wizard_data / set_easy_genre)
- APIキー検証状態の取得・設定・リセット
- APIキー入力欄の取得・設定
- 再描画回数(rerun_count)の取得・インクリメント
"""
from __future__ import annotations

from typing import Any

from streamlit_app.stores.base import BaseStore


class SessionStore(BaseStore):
    """セッション/ランタイム設定の状態アクセスをカプセル化するストア。"""

    # ==========================================================================
    # Wizard & Genre Settings
    # ==========================================================================
    @staticmethod
    def set_wizard_step(step: int) -> None:
        """ウィザードのステップを更新し、保存する"""
        SessionStore.update(lambda s: setattr(s.wizard, "step", step), notify_keys=["wizard_step"])

    @staticmethod
    def update_wizard_data(data: dict[str, Any]) -> None:
        """ウィザードの入力データを一括更新し、保存する"""
        SessionStore.update(lambda s: setattr(s.wizard, "data", data), notify_keys=["wizard_data"])

    @staticmethod
    def set_easy_genre(genre_key: str) -> None:
        """簡易モードのジャンル設定を更新する"""
        SessionStore.update(lambda s: setattr(s.runtime, "easy_genre_key", genre_key), notify_keys=["easy_genre_key"])

    # ==========================================================================
    # API Key Validation
    # ==========================================================================
    @staticmethod
    def get_api_key_validation_state() -> str:
        """APIキー検証状態を返す。("idle" / "pending" / "valid" / "invalid" / "error")"""
        return SessionStore.get_runtime().api_key_validation_state

    @staticmethod
    def set_api_key_validation_state(state: str) -> None:
        """APIキー検証状態をセット"""
        SessionStore.update_runtime("api_key_validation_state", state)

    @staticmethod
    def get_api_key_validation_key() -> str:
        """最後に検証したAPIキー値を返す"""
        return SessionStore.get_runtime().api_key_validation_key

    @staticmethod
    def set_api_key_validation_key(key: str) -> None:
        """最後に検証したAPIキー値を保存"""
        SessionStore.update_runtime("api_key_validation_key", key)

    @staticmethod
    def get_api_key_validation_error() -> str:
        """APIキー検証エラーメッセージを返す"""
        return SessionStore.get_runtime().api_key_validation_error

    @staticmethod
    def set_api_key_validation_error(msg: str) -> None:
        """APIキー検証エラーメッセージをセット"""
        SessionStore.update_runtime("api_key_validation_error", msg)

    @staticmethod
    def reset_api_key_validation() -> None:
        """APIキー検証状態を完全リセット"""
        SessionStore.update(lambda s: (
            setattr(s.runtime, "api_key_validation_state", "idle"),
            setattr(s.runtime, "api_key_validation_error", ""),
        ))

    # ==========================================================================
    # API Key Input & Rerun
    # ==========================================================================
    @staticmethod
    def get_api_key_input() -> str:
        """APIキー入力欄の値を取得する"""
        return SessionStore.get_runtime().api_key_input

    @staticmethod
    def set_api_key_input(value: str) -> None:
        """APIキー入力欄の値を設定する"""
        SessionStore.update_runtime("api_key_input", value)
