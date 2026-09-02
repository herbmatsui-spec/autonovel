"""
src/shared/network.py - � ネットワーク関連のユーティリティ
"""

import uuid


class NetworkUtils:
    @staticmethod
    def generate_connection_id() -> str:
        """Generate a unique connection ID."""
        return str(uuid.uuid4())
