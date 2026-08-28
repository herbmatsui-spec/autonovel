"""ID生成ユーティリティ"""
import uuid

def generate_prefixed_id(prefix: str, length: int = 12) -> str:
    """プレフィックス付きの一意IDを生成"""
    return f"{prefix}_{uuid.uuid4().hex[:length]}"

