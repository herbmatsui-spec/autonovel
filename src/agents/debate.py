import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class NullDebateAgent:
    """ディベートを行うためのエージェントのスタブ/NullObject"""
    def __init__(self):
        pass

    async def run_debate(self, initial_concept: Dict[str, Any], rounds: int = 1) -> Dict[str, Any]:
        return {
            "final_concept": initial_concept,
            "debate_log": []
        }

