from typing import Any

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
    key_tropes: list[str] = Field(default_factory=list)


class StyleDefinition(BaseModel):
    name: str | None = None
    instruction: str | None = None
    dialogue_ratio: str | None = None
    syntax_rhythm: str | None = None
    metaphor_dna: str | None = None
    noise_dna: str | None = None
    golden_rules: str | None = None
    negative_prompt: str | None = None
    is_light: bool | None = None


class ArchetypePreset(BaseModel):
    visual_icon: str | None = None
    summary: str | None = None
    trend_tag: str | None = None
    plot_pattern: str | None = None
    cheat_scale: int | None = None
    growth_curve: str | None = None
    system_assist: int | None = None
    reality_cost: int | None = None
    cost_severity: int | None = None
    style_key: str | None = None
    default_target_eps: int | None = None
    default_word_count: int | None = None


class StorytellingPlugin(BaseModel):
    name: str | None = None
    genre: str | None = None
    emotion_curve: list[EmotionPhase] = Field(default_factory=list)
    plot_common_rules: str | None = None
    style_presets: list[Any] = Field(default_factory=list)

    # Core Data-Driven Maps
    archetypes: dict[str, ArchetypePreset] | None = None
    style_definitions: dict[str, StyleDefinition] | None = None
    easy_mode_keywords: dict[str, str] | None = None

    # Optional dynamic config values
    villain_strategies: dict[str, str] | None = None
    debuff_profiles: dict[str, str] | None = None
    character_expansion_themes: dict[str, list[str]] | None = None
    anti_patterns: dict[str, list[str]] | None = None
    plot_structures: dict[str, PlotStructure] | None = None

    # Tropes / Trends config
    tropes: list[str] | None = None
    title_patterns: list[str] | None = None
    forbidden_words_replacements: dict[str, str] | None = None
