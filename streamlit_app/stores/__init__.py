"""
streamlit_app/stores — 状態管理クラスを機能別に分割したパッケージ。

UIStateStore が 475 行・40 以上の静的メソッドを持ち SRP に反していたため、
JobStore / SessionStore / PollStateStore / ToastStore 等へ責務を分割した。
各クラスは BaseStore を継承し、共通の状態アクセス基盤を再利用する。
"""
from streamlit_app.stores.base import BaseStore
from streamlit_app.stores.job_store import JobStore
from streamlit_app.stores.poll_store import PollStateStore
from streamlit_app.stores.session_store import SessionStore
from streamlit_app.stores.toast_store import ToastStore

__all__ = [
    "BaseStore",
    "JobStore",
    "PollStateStore",
    "ToastStore",
    "SessionStore",
]
