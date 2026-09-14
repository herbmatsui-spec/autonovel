"""下位互換性維持のためのエイリアス。実体は src.infrastructure.repositories に移動しました。"""
from src.infrastructure.repositories import *  # noqa: F401, F403
from src.infrastructure.repositories import __all__ as _all_exports
__all__ = _all_exports
