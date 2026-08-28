# Router endpoint helpers - to be implemented

from functools import wraps
from src.backend.task_helpers import create_task as _create_task

def workflow_endpoint(workflow_name: str):
    """ワークフローエンドポイントの共通処理デコレーター"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: 実装は次のステップで
            return await func(*args, **kwargs)
        return wrapper
    return decorator

