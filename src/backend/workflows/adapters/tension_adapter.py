"""
src/backend/workflows/adapters/tension_adapter.py - テンション曲線アダプタ
"""

from __future__ import annotations

from typing import Any


async def update_tension(hub: Any, ep: int, tension_value: float) -> None:
    """テンション値を hub に反映しエピソード情報を更新する"""
    val = float(tension_value)
    hub.tension_curve.append(val)
    hub.upsert_episode(int(ep), tension=val)
