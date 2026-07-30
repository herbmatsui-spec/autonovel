"""
src/core/state/state_manager.py — 後方互換 re-export
実体は streamlit_app/state_manager.py に移設済み。
"""

from streamlit_app.state_manager import SessionManager, get_session  # noqa: F401

__all__ = ["SessionManager", "get_session"]
