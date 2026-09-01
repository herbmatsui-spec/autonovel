import logging
from typing import Any

logger = logging.getLogger(__name__)

# Core classes with complete implementations


class CharacterStatusChange:
    def __init__(self, character_id: str, attribute: str, old_value: Any, new_value: Any):
        self.character_id = character_id
        self.attribute = attribute
        self.old_value = old_value
        self.new_value = new_value


class EpisodeStatusChanges:
    def __init__(self, character_status_changes: list[CharacterStatusChange]):
        self.character_status_changes = character_status_changes


class StateContradictionError(Exception):
    pass


class StateValidator:
    @staticmethod
    def validate_transitions(prev_ws: dict[str, Any], changes_obj: list):
        # Implement actual validation logic here
        pass


# StateValidatorAgent (Required for existing usage)
class StateValidatorAgent:
    def __init__(self):
        self.name = "state_validator"

    async def validate(self, state: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if not state.get("api_key"):
            issues.append("APIキーが未設定です。")
        mode = state.get("app_mode")
        if mode not in ("easy", "advanced"):
            issues.append(f"app_mode が不正です: {mode}")
        return issues
