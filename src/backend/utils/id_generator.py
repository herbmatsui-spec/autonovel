"""ID生成ユーティリティ"""
import uuid


def generate_prefixed_id(prefix: str, length: int = 16) -> str:
    """プレフィックス付きの一意IDを生成

    デフォルト 16 文字 (64bit) は UUIDv4 空間から生成され、
    100万件生成時の衝突確率は約 2.7e-8 (birthday paradox)。
    """
    return f"{prefix}_{uuid.uuid4().hex[:length]}"

