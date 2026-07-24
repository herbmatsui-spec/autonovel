"""
streamlit_app/utils/errors.py — 統一エラーハンドリング基盤
"""
from __future__ import annotations

import functools
import logging
from typing import Callable, Optional

import streamlit as st

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 共通例外クラス
# -----------------------------------------------------------------------------

class AppBaseException(Exception):
    """アプリケーション内のすべてのカスタム例外の基底クラス"""
    def __init__(self, message: str, detail: Optional[str] = None, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.recoverable = recoverable

class APIException(AppBaseException):
    """外部APIリクエストに関する例外"""
    pass

class EngineException(AppBaseException):
    """生成エンジン内部のロジックに関する例外"""
    pass

class ValidationError(AppBaseException):
    """入力バリデーションに関する例外"""
    pass

class StateException(AppBaseException):
    """セッション状態の不整合に関する例外"""
    pass

# -----------------------------------------------------------------------------
# UI通知ユーティリティ
# -----------------------------------------------------------------------------

class UIErrorHandler:
    """
    例外を解析し、ユーザーに適切な形式で通知するクラス。
    """
    @staticmethod
    def notify(e: Exception):
        """
        例外の種類に応じて、st.error, st.warning, st.toast などを使い分けて通知する。
        """
        if isinstance(e, AppBaseException):
            # カスタム例外の場合
            msg = e.message
            if not e.recoverable:
                st.error(f"🚨 重大なエラーが発生しました: {msg}")
                if e.detail:
                    st.caption(f"詳細: {e.detail}")
            else:
                st.warning(f"⚠️ {msg}")
                if e.detail:
                    st.caption(f"詳細: {e.detail}")
        else:
            # 予期せぬシステム例外の場合
            st.error(f"💥 予期しないエラーが発生しました: {str(e)}")
            logger.exception("Unhandled exception occurred")

    @staticmethod
    def toast_error(message: str, icon: str = "❌"):
        """簡易的なエラー通知"""
        st.toast(message, icon=icon)

# -----------------------------------------------------------------------------
# エラーハンドリング・デコレータ
# -----------------------------------------------------------------------------

def handle_errors(recoverable: bool = True, default_msg: str = "処理中にエラーが発生しました"):
    """
    関数をラップし、発生した例外を UIErrorHandler 経由で通知しつつ、
    適切にログを記録するデコレータ。
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppBaseException as e:
                # 既知のカスタム例外はそのままUIに渡す
                UIErrorHandler.notify(e)
                return None
            except Exception as e:
                # 未知の例外はラップして通知
                logger.exception(f"Error in {func.__name__}: {e}")
                wrapped_e = AppBaseException(
                    message=default_msg,
                    detail=str(e),
                    recoverable=recoverable
                )
                UIErrorHandler.notify(wrapped_e)
                return None
        return wrapper
    return decorator


class AppErrorHandler:
    @staticmethod
    def handle(exc, message=""):
        import logging
        logging.error(f"{message}: {exc}")

    @staticmethod
    def show_connection_error():
        import streamlit as st
        st.error("Backend connection error.")
