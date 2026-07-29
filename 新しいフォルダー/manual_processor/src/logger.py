# manual_processor/src/logger.py
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

def get_logger(name: str) -> logging.Logger:
    """
    アプリケーション共通のロガーを取得
    
    Args:
        name: ロガー名
    
    Returns:
        設定済みのLoggerインスタンス
    """
    logger = logging.getLogger(name)
    return logger


def setup_logger(name: str, log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """
    ロガーを初期化・設定する
    
    Args:
        name: ロガー名
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: ログファイルパス（オプション）
    
    Returns:
        設定済みのLoggerインスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 既存のハンドラーをクリア（重複防止）
    logger.handlers.clear()
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（指定がある場合）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 伝播を防止（ルートロガーへの二重出力防止）
    logger.propagate = False
    
    return logger


def set_third_party_log_levels():
    """サードパーティライブラリのログレベルを調整"""
    # Google Cloud ライブラリ
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('google.api_core').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    
    # その他
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fpdf').setLevel(logging.WARNING)


def configure_root_logger(log_level: str = "INFO", log_file: Optional[Path] = None):
    """
    ルートロガーを設定（アプリケーション起動時に1回呼び出す）
    
    Args:
        log_level: ルートログレベル
        log_file: ログファイルパス
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 既存ハンドラーをクリア
    root_logger.handlers.clear()
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソール
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイル
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # サードパーティ調整
    set_third_party_log_levels()


# 便利関数
def get_module_logger(module_name: str) -> logging.Logger:
    """モジュール用のロガーを取得（呼び出し元のモジュール名を自動取得）"""
    import inspect
    frame = inspect.currentframe().f_back
    caller_module = frame.f_globals.get('__name__', module_name)
    return logging.getLogger(caller_module)