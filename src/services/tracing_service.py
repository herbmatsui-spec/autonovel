import contextvars
import logging
import uuid
from typing import Optional

# コンテキスト変数として相関IDを管理
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

import json
from datetime import datetime


class CorrelationFilter(logging.Filter):
    """ログレコードに相関IDを付与するフィルタ"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "N/A"
        return True

class JsonLogFormatter(logging.Formatter):
    """構造化JSONログ用のフォーマッタ"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": getattr(record, 'correlation_id', "N/A"),
            "filename": record.filename,
            "lineno": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

def setup_tracing(log_level: int = logging.INFO, log_file: Optional[str] = "app.log"):
    """
    アプリケーション全体の構造化ロギングとトレーサビリティを設定する。
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # 既存のハンドラをクリア
    if logger.hasHandlers():
        logger.handlers.clear()

    # 相関IDを出力するカスタムフォーマッタ
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [TraceID: %(correlation_id)s] [%(name)s] %(message)s'
    )

    # フィルタ
    corr_filter = CorrelationFilter()

    # コンソール出力
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.addFilter(corr_filter)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # ファイル出力 (JSON構造化ログ)
    if log_file:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        fh.setLevel(log_level)
        fh.addFilter(corr_filter)
        fh.setFormatter(JsonLogFormatter())
        logger.addHandler(fh)

def set_correlation_id(cid: Optional[str] = None) -> str:
    """新しい相関IDを発行し、コンテキストにセットする"""
    new_id = cid or str(uuid.uuid4())
    correlation_id_var.set(new_id)
    return new_id

def get_correlation_id() -> Optional[str]:
    """現在の相関IDを取得する"""
    return correlation_id_var.get()

class TracingContext:
    """with文でスコープ内の相関IDを管理するコンテキストマネージャ"""
    def __init__(self, cid: Optional[str] = None):
        self.cid = cid or str(uuid.uuid4())
        self.token = None

    def __enter__(self):
        self.token = correlation_id_var.set(self.cid)
        return self.cid

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            correlation_id_var.reset(self.token)
