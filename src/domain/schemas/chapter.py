from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class SceneBeat(AutoNovelBaseSchema):
    """プロットから分解された物理動作・五感ビート（v4より完全継承）"""
    beat_num: int = Field(..., description="ビート番号")
    physical_action: str = Field(..., description="肉体的な動作描写")
    sensory_tags: List[str] = Field(
        default_factory=list,
        description="五感タグ: smell(嗅覚), sound(聴覚), touch(触覚), taste(味覚), sight(視覚)",
    )
    emotion_phase: str = Field(
        default="neutral",
        description="感情フェーズ: buildup(助走) / explosion(爆発) / aftermath(余韻)",
    )
    word_budget: int = Field(default=300, description="このビートに配分する目標文字数")

class CliffhangerDef(AutoNovelBaseSchema):
    """Web小説の離脱を防ぐ引き・クリフハンガー3分類（v4より完全継承）"""
    type: Literal["New Crisis", "Shocking Truth", "Quiet Foreshadowing"] = Field(
        default="New Crisis",
        description="引きの分類（新たな危機 / 衝撃の真実 / 静かな伏線）",
    )
    description: str = Field(..., description="クリフハンガーの具体的な描写・引きのフック")

class EmotionalHookSpec(AutoNovelBaseSchema):
    """読者の感情を揺さぶりカタルシスを生む感情フック（v4より完全継承）"""
    hook_type: str = Field(default="catharsis", description="カタルシス / 共感 / 緊張感 / ギャップ萌え")
    target_scene: str = Field(default="", description="フックを仕掛けるシーン")
    appeal_point: str = Field(default="", description="読者への最大の訴求ポイント")

class ChapterSchema(TimestampedSchema):
    id: int
    book_id: int
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., max_length=200)
    content: str = Field(default="")
    digest: str = Field(default="", max_length=300)  # 3層記憶用の100〜200字の事実要約
    word_count: int = 0
    status: str = Field(default="draft")  # draft, writing, completed, archived

    # プロットアイデア・ビートシート詳細
    scene_beats: List[SceneBeat] = Field(default_factory=list)
    cliffhanger: Optional[CliffhangerDef] = None
    emotional_hook: Optional[EmotionalHookSpec] = None

class ChapterCreateRequest(AutoNovelBaseSchema):
    book_id: int
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    outline: str = Field(default="")
    scene_beats: List[SceneBeat] = Field(default_factory=list)
    cliffhanger: Optional[CliffhangerDef] = None
    emotional_hook: Optional[EmotionalHookSpec] = None

class ChapterGenerateRequest(AutoNovelBaseSchema):
    chapter_id: int
    instruction: str = Field(default="")
    temperature: float = 0.7
