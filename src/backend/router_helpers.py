# Router endpoint helpers - to be implemented

from functools import wraps


def workflow_endpoint(workflow_name: str):
    """ワークフローエンドポイントの共通処理デコレーター"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: 実装は次のステップで
            return await func(*args, **kwargs)
        return wrapper
    return decorator

