# src/utils/context_compression_config.py
"""Context Compression 設定読み込みユーティリティ（互換レイヤー）"""
from __future__ import annotations

from src.services.compression.models import (
    SudachiConfig,
    CompressionConfig,
    load_compression_config,
    get_compression_config,
)

__all__ = [
    "SudachiConfig",
    "CompressionConfig",
    "load_compression_config",
    "get_compression_config",
]
