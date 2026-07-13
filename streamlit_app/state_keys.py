"""
streamlit_app/state_keys.py — st.session_state のキー定数管理
"""
from typing import Final

# アプリ全体で共有されるセッション状態のキーを定数化し、タイポの防止と管理を容易にする。

# -----------------------------------------------------------------------------
# Core Application State
# -----------------------------------------------------------------------------
# AppStateModel 自体を格納するキー
APP_STATE_KEY: Final[str] = "app_state_model"

# -----------------------------------------------------------------------------
# UI / Flow Control Flags (Boolean)
# -----------------------------------------------------------------------------
# CSSが注入済みかどうか
CSS_INJECTED_KEY: Final[str] = "css_injected"

# 各タブの初期化済みフラグ
EASY_MODE_LOADED_KEY: Final[str] = "easy_mode_loaded"
PLANNING_TAB_LOADED_KEY: Final[str] = "planning_tab_loaded"

# コンテンツ閲覧同意フラグ
NSFW_CONSENTED_KEY: Final[str] = "nsfw_consented"

# -----------------------------------------------------------------------------
# UI State
# -----------------------------------------------------------------------------
UI_STATE_KEY: Final[str] = "ui_state"

# -----------------------------------------------------------------------------
# Dynamic / Component-specific Keys (Prefixes)
# -----------------------------------------------------------------------------
# ログのスクロール位置などの動的キーに使用するプレフィックス
LOG_INDEX_PREFIX: Final[str] = "log_idx_"
