"""
src/core/state/state_manager.py — Streamlit セッション状態の型安全な管理
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from pydantic import BaseModel, Field

# 外部スキーマ定義からインポート
from schemas.app_state import AppStateModel

logger = logging.getLogger(__name__)

class WizardState(BaseModel):
    """ウィザード形式の入力状態を管理するモデル"""
    step: int = 1
    data: dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = False

class SessionManager:
    """
    UIStateStore / AppStateModel と st.session_state の同期、および永続化を管理するクラス。
    """
    _STATE_KEY = "app_state_model"

    @classmethod
    def _get_storage_path(cls) -> Path:
        """セッション固有の保存パスを生成する"""
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
                # active_jobはシリアライズ不能なため除外
                f.write(state.model_dump_json(indent=2, exclude={"active_job"}))
        except Exception as e:
            logger.error(f"Session state save failed: {e}")

    @classmethod
    def _load_from_disk(cls) -> Optional[AppStateModel]:
        """JSON ファイルから状態を復元する"""
        try:
            save_path = cls._get_storage_path()
            if save_path.exists():
                with open(save_path, "r", encoding="utf-8") as f:
                    data = f.read()
                    return AppStateModel.model_validate_json(data)
        except Exception as e:
            logger.error(f"Session state load failed: {e}")
        return None

    @classmethod
    def reset(cls) -> None:
        """状態をリセットする"""
        if cls._STATE_KEY in st.session_state:
            del st.session_state[cls._STATE_KEY]

def get_session() -> AppStateModel:
    """現在のセッション状態を返すショートカット"""
    return SessionManager.get_state()
