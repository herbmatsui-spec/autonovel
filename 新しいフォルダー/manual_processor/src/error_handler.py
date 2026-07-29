# manual_processor/src/error_handler.py
import logging
import traceback
from pathlib import Path
from .logger import log_exception, get_logger

def handle_error(error: Exception, context: str = "", logger: logging.Logger = None, 
                  show_user_notification: bool = True) -> bool:
    """
    エラーを適切に処理し、ログに記録してユーザーに通知
    
    Args:
        error: 捕捉された例外
        context: エラー発生時の状況説明
        logger: 使用するロガー（None指定でデフォルト使用）
        show_user_notification: ユーザー通知を表示するか
    
    Returns:
        bool: エラー処理が成功した場合True、重大エラー時False
    """
    if logger is None:
        logger = get_logger("error_handler")
    
    # 例外詳細をログに記録
    log_exception(error, logger, f"{context} エラー", reraise=True)
    
    # 重要なエラーの場合はユーザー通知を表示
    if show_user_notification and context:
        try:
            message = f"エラーが発生しました: {context}"
            # Pythonの例外表示を単純化
            message += f"
技術的な詳細: {type(error).__name__}"
            
            # 簡易UI通知（実際のGUI実装依存）
            print(f"[ERROR] {message}")
        except Exception as e:
            logger.error(f"ユーザー通知表示失敗: {e}")
    
    # 再起動不要のエラーは処理を継続
    return error.__class__.__name__ not in [
        "IOError", "FileNotFoundError", "PermissionError"
    ]

# エラーラッパー関数
def wrap_operation(operation, 
                  context: str = "", 
                  show_notification: bool = True):
    """
    操作をラップしてエラー処理を追加
    
    Args:
        operation: 関数型
        context: 操作説明
        show_notification: エラーメッセージ表示
    
    Returns:
        operationの戻り値
    """
    try:
        result = operation()
        return result
    except Exception as e:
        handled = handle_error(e, context, show_user_notification=show_notification)
        if not handled:
            raise  # 重要エラーは再発生
        return None