"""Multimedia 機能のフィーチャーフラグ判定ユーティリティ。

`ENABLE_MULTIMEDIA` が無効なとき、関連するエンドポイントは 503 を返す。
"""
from __future__ import annotations

from src.backend.config import settings
from src.backend.exceptions import MultimediaDisabledError

__all__ = [
    "is_multimedia_enabled",
    "is_audio_synth_enabled",
    "require_multimedia",
    "require_audio_synth",
]


def is_multimedia_enabled() -> bool:
    """Multimedia 系エンドポイント群が有効か。"""
    return bool(getattr(settings, "ENABLE_MULTIMEDIA", False))


def is_audio_synth_enabled() -> bool:
    """音声合成パイプラインが有効か。"""
    return bool(getattr(settings, "ENABLE_AUDIO_SYNTH", False))


def require_multimedia() -> None:
    """Multimedia が無効なら例外。"""
    if not is_multimedia_enabled():
        raise MultimediaDisabledError("Multimedia features are disabled (ENABLE_MULTIMEDIA=false)")


def require_audio_synth() -> None:
    """音声合成が無効なら例外。"""
    if not is_audio_synth_enabled():
        raise MultimediaDisabledError("Audio synthesis is disabled (ENABLE_AUDIO_SYNTH=false)")
