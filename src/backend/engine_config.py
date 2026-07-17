"""
engine_config.py - エンジン構築用の軽量設定オブジェクト。

UltimateHegemonyEngine が抱えていた「42引数爆発」の根本原因（プリミティブ型の
位置引数執着）を解消するため、エンジン構築に必要なランタイム設定を
1つの frozen dataclass に集約する。
"""
from __future__ import annotations

from dataclasses import dataclass

from src.backend.engine_utils import AdaptiveCooldown


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """エンジン構築に必要なランタイム設定をまとめた不変オブジェクト。"""

    api_key: str
    cooldown: AdaptiveCooldown

    @classmethod
    def create(
        cls,
        api_key: str,
        cooldown: AdaptiveCooldown | None = None,
    ) -> "EngineConfig":
        """デフォルト冷却設定で EngineConfig を生成するファクトリ。"""
        if cooldown is None:
            cooldown = AdaptiveCooldown(base_sec=2.0, min_sec=0.5, max_sec=10.0)
        return cls(api_key=api_key, cooldown=cooldown)
