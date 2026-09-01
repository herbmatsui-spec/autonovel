"""
routers/system.py - システム状態・耐障害モード API

DB/Gemini の到達性とオフラインモード状態を報告する。
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from src.services import resilience

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """システム全体の耐障害ステータスを返す。"""
    return resilience.get_system_status()


@router.get("/offline")
async def offline_flag() -> Dict[str, Any]:
    """オフラインモード有効状態を返す。"""
    return {
        "offline_mode_enabled": resilience.is_offline_mode_enabled(),
        "cache_first": resilience.is_offline_mode_enabled(),
    }
