"""Engine helper functions."""

from src.backend.engine_config import EngineConfig
from src.backend.engine_facade import EngineFacade
from src.backend.orchestrator_engine_adapter import OrchestratorEngineAdapter
from src.agents.orchestrator import Orchestrator, AgentName
from src.agents.skill_base import SkillAgent
from src.core.container.app import AppContainer


def get_engine(api_key: str) -> EngineFacade:
    """APIキーからエンジンインスタンスを生成する。

    Orchestrator を内包した OrchestratorEngineAdapter を EngineFacade でラップして返す。
    これにより呼び出し側 (routers / streamlit) は engine.* インターフェースを
    そのまま利用できる。
    """
    container = AppContainer(api_key=api_key)
    return container.engine_facade()
