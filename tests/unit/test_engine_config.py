"""EngineConfig のユニットテスト。"""
from src.backend.engine_config import EngineConfig
from src.backend.engine_utils import AdaptiveCooldown


def test_create_with_default_cooldown():
    cfg = EngineConfig.create(api_key="test-key")
    assert cfg.api_key == "test-key"
    assert isinstance(cfg.cooldown, AdaptiveCooldown)


def test_create_with_explicit_cooldown():
    cd = AdaptiveCooldown(base_sec=1.0, min_sec=0.2, max_sec=5.0)
    cfg = EngineConfig.create(api_key="k", cooldown=cd)
    assert cfg.cooldown is cd


def test_frozen_invariant():
    cfg = EngineConfig.create(api_key="k")
    try:
        cfg.api_key = "other"  # type: ignore[attr-defined]
    except Exception:
        # frozen dataclass は上書き時に例外を投げる（実装依存）
        pass
    # 少なくとも api_key は保存されている
    assert cfg.api_key == "k"
