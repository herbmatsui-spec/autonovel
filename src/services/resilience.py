"""
services/resilience.py - オフライン／低帯域耐障害モードの状態判定

バックエンド（DB）・Gemini API の到達性を確認し、
オフライン時はセマンティックキャッシュ優先で動作するよう状態を報告する。
ネットワーク遮断時も例外を投げず、安全に offline 状態を返す。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def is_offline_mode_enabled() -> bool:
    """環境変数 OFFLINE_MODE でオフラインモードが有効かを返す。"""
    return os.environ.get("OFFLINE_MODE", "false").lower() in ("1", "true", "yes")


def check_database() -> str:
    """DB の到達性を確認する（ok/error）。"""
    try:
        from src.core.container import AppContainer

        mgr = AppContainer.db()
        # 同期的な軽い確認
        import asyncio

        async def _ping():
            async with mgr.engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

        asyncio.get_event_loop().run_until_complete(_ping())
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"db check failed: {exc}")
        return "error"


def check_gemini() -> str:
    """Gemini API の到達性を確認する（ok/error）。キー未設定時は disabled。"""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "disabled"
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        # 軽量なモデル一覧取得で到達性を確認
        list(genai.list_models())
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"gemini check failed: {exc}")
        return "error"


def get_system_status() -> Dict[str, Any]:
    """システム全体の耐障害ステータスを返す。"""
    db = check_database()
    gemini = check_gemini()
    offline = is_offline_mode_enabled() or gemini == "error"
    if offline:
        mode = "offline" if is_offline_mode_enabled() else "degraded"
    else:
        mode = "online"
    return {
        "mode": mode,
        "offline_mode_enabled": is_offline_mode_enabled(),
        "database": db,
        "gemini": gemini,
        "cache_first": offline,
        "recommendation": (
            "オフライン: セマンティックキャッシュからの再開を推奨"
            if offline
            else "オンライン: 通常通り生成可能"
        ),
    }
