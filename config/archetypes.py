from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class CommercialRole(str, Enum):
    AVATAR_OF_DESIRE = "avatar_of_desire"
    HATE_MAGNET = "hate_magnet"
    UNCONDITIONAL_SUPPORTER = "unconditional_supporter"
    CONTRAST_ENGINE = "contrast_engine"
    UNIQUE_VALUE = "unique_value"
    GROWTH_INVESTMENT = "growth_investment"
    DESTINED_RESONANCE = "destined_resonance"
    INFORMATION_HEGEMONY = "information_hegemony"
    STATUS_FLIP_TRIGGER = "status_flip_trigger"

COMMERCIAL_ROLE_DESCRIPTIONS = {
    role.value: f"Description for {role.value}" for role in CommercialRole
}

DEFAULT_COMMERCIAL_ROLES = [
    CommercialRole.AVATAR_OF_DESIRE,
    CommercialRole.HATE_MAGNET,
]

ROLE_REQUIRED_ATTRIBUTES = {
    role.value: ["base_power", "personality"] for role in CommercialRole
}

PLEASURE_TRIGGER_KEYWORDS = {
    role.value: ["trigger1", "trigger2"] for role in CommercialRole
}

GAP_ATTRIBUTE_PAIRS = {
    "cold_exterior": "warm_interior",
    "weak_start": "hidden_power",
}

DESTINED_RESONANCE_PATTERNS = {
    "fated_encounter": "high_sync",
}

STATUS_FLIP_TIMING = {
    "mid_flip": {"trigger_position": 0.5, "impact_modifier": 1.2},
}

INFORMATION_HEGEMONY_PATTERNS = {
    "hidden_knowledge": "strategic_advantage",
}

GROWTH_INVESTMENT_PHASES = {
    "early": "potential_accumulation",
    "mid": "rapid_growth",
    "late": "harvest_phase",
}

class CharacterCommercialMeta(BaseModel):
    primary_role: CommercialRole
    secondary_roles: List[CommercialRole] = Field(default_factory=list)
    recognition_value: float = 1.0
    pleasure_keywords: List[str] = Field(default_factory=list)
    trigger_positions: List[float] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

def calculate_recognition_value(base_power: float, rarity: int) -> float:
    return base_power * (1 + rarity * 0.1)

def assign_commercial_role(profile: Dict[str, Any]) -> List[str]:
    return [CommercialRole.AVATAR_OF_DESIRE.value]

def get_role_pleasure_keywords(roles: List[str]) -> List[str]:
    keywords = []
    for r in roles:
        keywords.extend(PLEASURE_TRIGGER_KEYWORDS.get(r, []))
    return keywords

def validate_character_commercial_value(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {"is_valid": True, "missing_attributes": []}

def get_gap_attribute_pair(profile: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    return ("cold_exterior", "warm_interior")

def get_status_flip_timing_config(timing_key: str) -> Dict[str, Any]:
    return STATUS_FLIP_TIMING.get(timing_key, {})
