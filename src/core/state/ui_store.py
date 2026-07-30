"""
src/core/state/ui_store.py — 後方互換 re-export
実体は streamlit_app/ui_store.py に移設済み。
"""

from streamlit_app.ui_store import UIStateStore  # noqa: F401

__all__ = ["UIStateStore"]
