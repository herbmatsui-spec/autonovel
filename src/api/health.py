"""
src/api/health.py - DEPRECATED: Use src.backend.routers.health instead.
Compatibility shim for legacy health router imports.
"""

from src.backend.routers.health import router

__all__ = ["router"]