"""Engine helper functions."""
from src.backend.engine import UltimateHegemonyEngine
from src.backend.engine_config import EngineConfig
from src.backend.engine_facade import EngineFacade
from src.core.container import make_container


def get_engine(api_key: str) -> EngineFacade:
    """APIキーからエンジンインスタンスを生成する。

    現時点では UltimateHegemonyEngine を内包した EngineFacade を返す。
    これにより呼び出し側 (routers / streamlit) は engine.* インターフェースを
    そのまま利用でき、将来のサービス分解 (ADR-0004) も影響なしに進められる。
    """
    container = make_container(api_key)
    legacy_engine = container.engine()
    config = EngineConfig.create(api_key=api_key, cooldown=legacy_engine.cooldown)
    return EngineFacade(config=config, engine=legacy_engine)
