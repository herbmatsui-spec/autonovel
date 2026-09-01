from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmotionPhase(BaseModel):
    phase: str
    target_emotion: str = ""
    description: str = ""
    intensity: int = 50
    instruction: str = ""


class PlotStructure(BaseModel):
    name: str
    hook: str = ""
    mid_crisis: str = ""
    climax_type: str = ""
    ending: str = ""
    key_tropes: List[str] = Field(default_factory=list)


class StyleDefinition(BaseModel):
    name: Optional[str] = None
    instruction: Optional[str] = None
    dialogue_ratio: Optional[str] = None
    syntax_rhythm: Optional[str] = None
    metaphor_dna: Optional[str] = None
    noise_dna: Optional[str] = None
    golden_rules: Optional[str] = None
    negative_prompt: Optional[str] = None
    is_light: Optional[bool] = None


class ArchetypePreset(BaseModel):
    visual_icon: Optional[str] = None
    summary: Optional[str] = None
    trend_tag: Optional[str] = None
    plot_pattern: Optional[str] = None
    cheat_scale: Optional[int] = None
    growth_curve: Optional[str] = None
    system_assist: Optional[int] = None
    reality_cost: Optional[int] = None
    cost_severity: Optional[int] = None
    style_key: Optional[str] = None
    default_target_eps: Optional[int] = None
    default_word_count: Optional[int] = None


class StorytellingPlugin(BaseModel):
    name: Optional[str] = None
    genre: Optional[str] = None
    emotion_curve: List[EmotionPhase] = Field(default_factory=list)
    plot_common_rules: Optional[str] = None
    style_presets: List[Any] = Field(default_factory=list)

    # Core Data-Driven Maps
    archetypes: Optional[Dict[str, ArchetypePreset]] = None
    style_definitions: Optional[Dict[str, StyleDefinition]] = None
    easy_mode_keywords: Optional[Dict[str, str]] = None

    # Optional dynamic config values
    villain_strategies: Optional[Dict[str, str]] = None
    debuff_profiles: Optional[Dict[str, str]] = None
    character_expansion_themes: Optional[Dict[str, List[str]]] = None
    anti_patterns: Optional[Dict[str, List[str]]] = None
    plot_structures: Optional[Dict[str, PlotStructure]] = None

    # Tropes / Trends config
    tropes: Optional[List[str]] = None
    title_patterns: Optional[List[str]] = None
    forbidden_words_replacements: Optional[Dict[str, str]] = None
