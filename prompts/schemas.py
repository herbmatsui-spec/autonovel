from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PromptContext(BaseModel):
    """プロンプトコンテキストの基底モデル。"""

    model_config = ConfigDict(extra="allow")

    book_id: int | None = None
    template_name: str | None = None


class AuditContext(PromptContext):
    """監査系プロンプトのコンテキスト。"""

    synopsis: str = ""
    world_settings_json: str = "{}"
    response_schema_json: str | dict[str, Any] = "{}"
    past_facts: str = ""
    plot_bp: str = ""
    script: str = ""
    f_map: list[dict[str, Any]] | None = None
    content: str = ""
    scene_content: str = ""
    context: str = ""
    previous_metrics: str | None = None
    curve_str: str = ""
    ep_num: int = 1
    current_tension: int = 50
    action: str = ""
    reason: str = ""
    conflict_report: str = ""
    world_rules: str = ""
    mc_profile: str = ""
    blueprint: str = ""
    settings_json: str = "{}"
    characters_json: str = "{}"


class WritingContext(PromptContext):
    """執筆系プロンプトのコンテキスト。"""

    title: str = ""
    ep_num: int = 1
    static_ctx: str = ""
    dyn_ctx: str = ""
    prev_ctx: str = ""
    blueprint: str = ""
    extra_instruction: str = ""
    target_word_count: int = 3000
    char_static_ctx: str = ""
    char_dynamic_ctx: str = ""
    plot_data: dict[str, Any] = Field(default_factory=dict)
    script_text: str = ""
    style_key: str = "style_web_standard"
    write_rule_type: str = "RULE_SET_A"
    settings_ctx: str | dict[str, Any] = "{}"
    director_notes: str | None = None
    divergence_type_name: str = "safe"
    density_level: str = "Standard"
    pov_character_name: str = ""
    dialogue_profiles: dict[str, Any] = Field(default_factory=dict)
    use_beat_rules: bool = True
    draft_content: str = ""
    prose_sample: str = ""
    is_light: bool = False
    fix_inst: str = ""


class PlotExpansionContext(PromptContext):
    """プロット展開系プロンプトのコンテキスト。"""

    book_title: str = ""
    ep_num: int = 1
    ep_info: Any = None
    past_plots: list[Any] = Field(default_factory=list)
    arcs: list[Any] = Field(default_factory=list)
    book_genre: str = ""
    emotional_hook: Any = None
    bible_json_str: str = "{}"
    ep_range: list[int] = Field(default_factory=list)
    engine_key: str = "conflict"


class UtilityContext(PromptContext):
    """ユーティリティ系プロンプト（マーケティング、タイトル等）のコンテキスト。"""

    genre: str = ""
    keywords: str = ""
    trend_memo: str = ""
    book_title: str = ""
    synopsis: str = ""
    latest_ep: int = 1
    sample_text: str = ""
    bible_core_concept: str = ""
    bible_core_title: str = ""
    bible_core_synopsis: str = ""
    target_eps: int = 10
    world_rules_json: str = "{}"
    concept: str = ""
    roadmap_list_schema: Any = None
    mc_data_json: str = "{}"
    causality_map: list[str] = Field(default_factory=list)
    mc_name: str = ""
    cleaned_content: str = ""
    episode_draft_schema: Any = None
    plot_summary: str = ""
    rough_plot: str = ""
    opening_500_chars: str = ""
    summary_data_json: str = ""
    book_genre: str = ""
    batch_data: str = ""
    engine_key: str = "conflict"
    style_key: str = "style_web_standard"
