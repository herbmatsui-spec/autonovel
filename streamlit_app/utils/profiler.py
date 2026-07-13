"""
streamlit_app/utils/profiler.py — UI/Backendパフォーマンス計測ユーティリティ
"""
import functools
import logging
import time
from typing import Callable

import streamlit as st

logger = logging.getLogger(__name__)

def profile_performance(name: str = None):
    """
    関数の実行時間を計測し、ログ出力およびStreamlitのトーストで通知するデコレータ。
    
    Args:
        name: 計測名。指定しない場合は関数名を使用する。
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            label = name or func.__name__
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time

                # ログへの出力
                logger.info(f"⏱️ [Profiler] {label}: {duration:.4f}s")

                # 1秒以上の処理はユーザーに通知（開発モード的に活用）
                if duration > 1.0:
                    st.toast(f"⌛ {label} に {duration:.2f}秒かかりました", icon="⏱️")

        return wrapper
    return decorator

class PerformanceTracker:
    """
    コンテキストマネージャ形式で特定のブロックの時間を計測する。
    """
    def __init__(self, label: str):
        self.label = label
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        logger.info(f"⏱️ [Profiler] {self.label}: {duration:.4f}s")
        if duration > 1.0:
            st.toast(f"⌛ {self.label} に {duration:.2f}秒かかりました", icon="⏱️")
