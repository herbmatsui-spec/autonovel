import logging
from typing import Any, Dict, List

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class StateValidatorAgent(BaseAgent):
    """ランタイム状態の不整合を検出するエージェント。"""

    async def validate(self, state: Dict[str, Any]) -> List[str]:
        issues: List[str] = []
        if not state.get("api_key"):
            issues.append("APIキーが未設定です。")
        mode = state.get("app_mode")
        if mode not in ("easy", "advanced"):
            issues.append(f"app_mode が不正です: {mode}")
        return issues

    async def run(self, *args, **kwargs):
        state = kwargs.get("state", {})
        return await self.validate(state)

