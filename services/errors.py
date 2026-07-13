import logging
from typing import Callable

logger = logging.getLogger(__name__)

class AppErrorHandler:
    @staticmethod
    def handle(error: Exception, context: str = "不明なエラー"):
        import streamlit as st
        logging.error(f"Error in {context}: {error}", exc_info=True)
        st.error(f"❌ {context}: {str(error)}")

    @staticmethod
    def show_connection_error():
        import streamlit as st
        st.warning(
            "⚠️ **バックエンドサーバーに接続できません。**\n"
            "サーバーが起動しているか確認してください。",
            icon="🚨"
        )

# retry_on_lock は src.services.errors から re-export
from src.services.errors import retry_on_lock  # noqa: F401

