"""
src/shared/event_bus.py - UI イベント型の薄い再エクスポート

kernels/ 配下のモジュールが streamlit_app/ へ直接依存しないようにするための
中継ぎモジュール。実体は streamlit_app.event_bus 側に存在する。
"""

from enum import Enum


class UIEventType(str, Enum):
    """UI イベント種別 (streamlit_app.event_bus.UIEventType と互換)。

    kernels 側はこの enum を介してのみイベント種別を参照する。
    """

    REQUEST_GENERATE_PLAN = "REQUEST_GENERATE_PLAN"
    REQUEST_AUDIT_PLAN = "REQUEST_AUDIT_PLAN"
    REQUEST_GENERATE_EPISODE = "REQUEST_GENERATE_EPISODE"
    REQUEST_CANCEL_JOB = "REQUEST_CANCEL_JOB"


__all__ = ["UIEventType"]
