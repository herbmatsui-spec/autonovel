from __future__ import annotations

from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS, StyleKey
from src.models.character import CharacterRegistry
from src.models.plot import ArcBlueprint, DynamicPacing, PlotEpisode, ReviewLog, RoadmapItem
from src.models.world import AnchorResponse, WorldRules


class StoryDNA(BaseModel):
    """
    物語の不変的な核（DNA）。
    これに基づいて執筆が進められ、5話ごとにリフレクションによって進化する。
    """

    core_concept: str = Field(default="", description="物語の究極の核、唯一無二の魅力")
    mc_immutable_core: str = Field(
        default="", description="主人公が絶対に失わない性質、執筆の絶対指針"
    )
    world_laws: str = Field(default="", description="世界の絶対的なルール、覆らない因果律")
    climax_vision: str = Field(default="", description="目指すべき最高潮の光景")
    marketing_hooks: list[str] = Field(
        default_factory=list, description="読者を惹きつける商業的キーワード"
    )
    mutation_history: list[str] = Field(
        default_factory=list, description="DNAの進化（リフレクション）履歴"
    )
    version: int = Field(default=1)

    model_config = MODEL_CONFIG_DEFAULTS


class MarketingAssets(BaseModel):
    catchcopies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    ab_test_candidates: list[dict] = Field(
        default_factory=list, description="タイトル・タグのABテスト案"
    )

    model_config = MODEL_CONFIG_DEFAULTS


class WorldBibleCore(BaseModel):
    dna: StoryDNA = Field(default_factory=StoryDNA)
    thought_process: str = Field(default="", description="企画全体の整合性チェック思考プロセス")
    genre: str = Field(default="ファンタジー")
    style_key: StyleKey = Field(default="style_web_standard")
    keywords: str = Field(default="")
    title: str = Field(default="無題")
    concept: str = Field(default="")
    target_persona: str = Field(default="")
    reader_promise: str = Field(default="")
    synopsis: str = Field(default="")
    world_settings: WorldRules = Field(default_factory=WorldRules)
    mc_profile: CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters: list[CharacterRegistry] = Field(default_factory=list)
    marketing_assets: MarketingAssets = Field(default_factory=MarketingAssets)
    arcs: list[ArcBlueprint] = Field(default_factory=list)
    review_logs: list[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: list[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: list[str] = Field(default_factory=list)
    story_direction: str = Field(default="")
    engine_key: str = Field(
        default="conflict", description="物語を駆動する4大アーキタイプエンジンキー"
    )
    absolute_dictionary: dict[str, str] = Field(
        default_factory=dict, description="固有名詞・キャラクター設定の絶対辞書（表記揺れ防止）"
    )

    model_config = MODEL_CONFIG_DEFAULTS


class WorldBible(BaseModel):
    id: int | None = Field(default=None)
    genre: str = Field(default="ファンタジー")
    style_key: StyleKey = Field(default="style_web_standard")
    keywords: str = Field(default="")
    title: str = Field(default="無題")
    concept: str = Field(default="")
    dna: StoryDNA = Field(default_factory=StoryDNA)
    synopsis: str = Field(default="")
    world_settings: WorldRules = Field(default_factory=WorldRules)
    mc_profile: CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters: list[CharacterRegistry] = Field(default_factory=list)
    marketing_assets: MarketingAssets = Field(default_factory=MarketingAssets)
    anchors: list[AnchorResponse] = Field(default_factory=list)
    arcs: list[ArcBlueprint] = Field(default_factory=list)
    plots: list[PlotEpisode] = Field(default_factory=list)
    thought_process: str = Field(default="")
    review_logs: list[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: list[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: list[str] = Field(default_factory=list)
    story_direction: str = Field(default="")
    full_story_roadmap: list[RoadmapItem] = Field(default_factory=list)
    engine_key: str = Field(
        default="conflict", description="物語を駆動する4大アーキタイプエンジンキー"
    )
    absolute_dictionary: dict[str, str] = Field(
        default_factory=dict, description="固有名詞・キャラクター設定の絶対辞書（表記揺れ防止）"
    )

    model_config = MODEL_CONFIG_DEFAULTS


class NovelStructure(BaseModel):
    title: str
    concept: str
    synopsis: str
    mc_profile: CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters: list[CharacterRegistry] = Field(default_factory=list)
    plots: list[PlotEpisode] = Field(default_factory=list)
    marketing_assets: MarketingAssets = Field(default_factory=MarketingAssets)
    anchors: list[AnchorResponse] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class UltraFastWorldBible(BaseModel):
    """超高速・統合生成用のPydanticモデル。世界設定、キャラ、ロードマップを1コールで取得する。"""

    bible_core: WorldBibleCore = Field(..., description="統合世界観・設定集")
    full_story_roadmap: list[RoadmapItem] = Field(..., description="作品全体の全話ロードマップ")

    model_config = MODEL_CONFIG_DEFAULTS
