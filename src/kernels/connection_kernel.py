"""
kernels/connection_kernel.py - 接続関連の基盤機能
"""

from typing import Any

from src.shared.network import NetworkUtils

from .base import KernelBase, KernelState
from .connection import Connection as BaseConnection


class ConnectionKernel(KernelBase):
    """
    接続関連機能を管理するカーネル
    """

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        super().__init__()
        self.api_key = api_key
        self.timeout = timeout
        self.connections: dict[str, BaseConnection] = {}

    async def connect(self, service_url: str) -> str:
        """サービスに接続"""
        if self.validate_context() and self.state == KernelState.INITIALIZED:
            self.set_state(KernelState.ACTIVE)
            # 実際の接続実装はベースクラスに委譲
            connection_id = NetworkUtils.generate_connection_id()
            connection = BaseConnection(self.api_key, self.timeout)
            self.connections[connection_id] = connection
            await connection.connect(service_url)
            return connection_id
        return "ERROR"

    async def disconnect(self, connection_id: str) -> bool:
        """接続を解除"""
        connection = self.connections.get(connection_id)
        if connection:
            await connection.disconnect()
            self.connections.pop(connection_id, None)
            return True
        return False

    async def send(self, connection_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """データを送信"""
        connection = self.connections.get(connection_id)
        if connection:
            return await connection.send(data)
        return {"error": "CONNECTION_NOT_FOUND"}

    def validate_context(self) -> bool:
        return True
