from __future__ import annotations

from typing import Dict, List, Optional

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
    mc_immutable_core: str = Field(default="", description="主人公が絶対に失わない性質、執筆の絶対指針")
    world_laws: str = Field(default="", description="世界の絶対的なルール、覆らない因果律")
    climax_vision: str = Field(default="", description="目指すべき最高潮の光景")
    marketing_hooks: List[str] = Field(default_factory=list, description="読者を惹きつける商業的キーワード")
    mutation_history: List[str] = Field(default_factory=list, description="DNAの進化（リフレクション）履歴")
    version: int = Field(default=1)

    model_config = MODEL_CONFIG_DEFAULTS

class MarketingAssets(BaseModel):
    catchcopies:       List[str]            = Field(default_factory=list)
    tags:              List[str]            = Field(default_factory=list)
    ab_test_candidates: List[dict]           = Field(default_factory=list, description="タイトル・タグのABテスト案")

    model_config = MODEL_CONFIG_DEFAULTS

class WorldBibleCore(BaseModel):
    dna:                 StoryDNA        = Field(default_factory=StoryDNA)
    thought_process:     str             = Field(default="", description="企画全体の整合性チェック思考プロセス")
    genre:               str             = Field(default="ファンタジー")
    style_key:           StyleKey        = Field(default="style_web_standard")
    keywords:            str             = Field(default="")
    title:               str             = Field(default="無題")
    concept:             str             = Field(default="")
    target_persona:      str             = Field(default="")
    reader_promise:      str             = Field(default="")
    synopsis:            str             = Field(default="")
    world_settings:      WorldRules      = Field(default_factory=WorldRules)
    mc_profile:          CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters:      List[CharacterRegistry] = Field(default_factory=list)
    marketing_assets:    MarketingAssets = Field(default_factory=MarketingAssets)
    arcs:                List[ArcBlueprint] = Field(default_factory=list)
    review_logs:         List[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: List[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: List[str] = Field(default_factory=list)
    story_direction:     str             = Field(default="")
    engine_key:          str             = Field(default="conflict", description="物語を駆動する4大アーキタイプエンジンキー")
    absolute_dictionary: Dict[str, str]  = Field(default_factory=dict, description="固有名詞・キャラクター設定の絶対辞書（表記揺れ防止）")

    model_config = MODEL_CONFIG_DEFAULTS

class WorldBible(BaseModel):
    id:                  Optional[int]   = Field(default=None)
    genre:               str             = Field(default="ファンタジー")
    style_key:           StyleKey        = Field(default="style_web_standard")
    keywords:            str             = Field(default="")
    title:               str             = Field(default="無題")
    concept:             str             = Field(default="")
    dna:                 StoryDNA        = Field(default_factory=StoryDNA)
    synopsis:            str             = Field(default="")
    world_settings:      WorldRules      = Field(default_factory=WorldRules)
    mc_profile:          CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters:      List[CharacterRegistry] = Field(default_factory=list)
    marketing_assets:    MarketingAssets = Field(default_factory=MarketingAssets)
    anchors:             List[AnchorResponse] = Field(default_factory=list)
    arcs:                List[ArcBlueprint] = Field(default_factory=list)
    plots:               List[PlotEpisode] = Field(default_factory=list)
    thought_process:     str             = Field(default="")
    review_logs:         List[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: List[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: List[str] = Field(default_factory=list)
    story_direction:     str             = Field(default="")
    full_story_roadmap:  List[RoadmapItem] = Field(default_factory=list)
    engine_key:          str             = Field(default="conflict", description="物語を駆動する4大アーキタイプエンジンキー")
    absolute_dictionary: Dict[str, str]  = Field(default_factory=dict, description="固有名詞・キャラクター設定の絶対辞書（表記揺れ防止）")

    model_config = MODEL_CONFIG_DEFAULTS

class NovelStructure(BaseModel):
    title:          str
    concept:        str
    synopsis:       str
    mc_profile:     CharacterRegistry        = Field(default_factory=CharacterRegistry)
    sub_characters: List[CharacterRegistry]  = Field(default_factory=list)
    plots:          List[PlotEpisode]        = Field(default_factory=list)
    marketing_assets: MarketingAssets        = Field(default_factory=MarketingAssets)
    anchors:        List[AnchorResponse]     = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class UltraFastWorldBible(BaseModel):
    """超高速・統合生成用のPydanticモデル。世界設定、キャラ、ロードマップを1コールで取得する。"""
    bible_core: WorldBibleCore = Field(..., description="統合世界観・設定集")
    full_story_roadmap: List[RoadmapItem] = Field(..., description="作品全体の全話ロードマップ")

    model_config = MODEL_CONFIG_DEFAULTS
