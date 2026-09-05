"""
streamlit_app/state.py — UI状態管理

Streamlit の session_state を型和でラップし、型安全にアクセス提供する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import streamlit as st


@dataclass
class UIStateStore:
    """グローバルUI状態 store"""

    config_data: dict[str, Any] = field(default_factory=dict)
    current_project_id: Optional[str] = None
    sidebar_collapsed: bool = False

    @staticmethod
    def get_runtime() -> "UIStateStore":
        if "runtime" not in st.session_state:
            st.session_state["runtime"] = UIStateStore()
        return st.session_state["runtime"]

    @staticmethod
    def update_runtime(key: str, value: Any) -> None:
        store = UIStateStore.get_runtime()
        setattr(store, key, value)


class ConfigState:
    """設定状態管理（メモリ上のみの一時的状態）"""

    _defaults: dict[str, Any] = {
        "enable_draft_polish": True,
        "enable_actor_critic": True,
        "enable_heavy_audit": True,
        "enable_nsfw": False,
        "erotic_intensity": 0,
        "safety_filter_level": "BLOCK_ONLY_HIGH",
        "cost_mode": "balanced",
        "max_history_len": 30,
        "auto_backup": True,
    }

    @classmethod
    def init_defaults(cls) -> None:
        for key, value in cls._defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        st.session_state[key] = value

    @staticmethod
    def update(**kwargs) -> None:
        for key, value in kwargs.items():
            st.session_state[key] = value

