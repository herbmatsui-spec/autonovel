from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class CharacterRelationSchema(AutoNovelBaseSchema):
    """キャラクター間の関係性（v4より完全継承）"""
    target_character_name: str
    relationship_type: str = Field(default="関係者", description="ライバル, 師弟, 依存, 秘密の恋人, 恩人, 宿敵")
    description: str = Field(default="", description="関係性の具体的な内容や背景")
    intensity: int = Field(default=3, ge=1, le=5, description="関係性の強度（1:希薄〜5:運命的）")
    secret_aspect: Optional[str] = Field(default=None, description="関係性の秘密の側面・裏の顔")

class CharacterSchema(TimestampedSchema):
    """心理学的・創作論的キャラクタープロファイル（v4より完全継承）"""
    id: int
    book_id: int
    name: str = Field(..., max_length=100)
    role: str = Field(default="sub", description="protagonist(主人公), antagonist(敵対者), sub(脇役)")
    gender: str = Field(default="")
    age: str = Field(default="")
    appearance: str = Field(default="", description="容姿・挿絵生成プロンプト用外見特徴")
    personality: str = Field(default="", description="基本的性格")

    # 心理・葛藤プロファイル (Save The Cat / 人間味)
    surface_persona: str = Field(default="", description="周囲からどう見られているか、演じている社会的仮面")
    inner_conflict: str = Field(default="", description="演じている自分と本当の望みの間の葛藤")
    core_trauma: str = Field(default="", description="過去のトラウマや原初の欠落")
    save_the_cat_event: str = Field(default="", description="読者が共感する人間味ある善行（Save the Cat）")
    social_mask_vs_truth: str = Field(default="", description="表向きの仮面と、夜一人の時の剥き出しの真実の対比")
    iron_constraint: str = Field(default="", description="絶対に破らない行動原則・鉄の禁忌")

    # 口調・文体・二層監査連動
    first_person: str = Field(default="私", description="一人称")
    second_person: str = Field(default="貴方", description="二人称")
    suffix_style: str = Field(default="", description="特徴的な語尾（例: 〜ですわ）")
    suffix_patterns: List[str] = Field(default_factory=list, description="静的監査用正規表現（例: ['ですわ$', 'ますわ$']）")
    dialogue_samples: List[str] = Field(default_factory=list, description="セリフサンプル")

    # Truth Ledger（事実認識の境界線: ハルシネーション・先回り防止）
    known_facts: List[str] = Field(default_factory=list, description="知っている事実")
    unknown_facts: List[str] = Field(default_factory=list, description="まだ知らない事実（絶対に漏らしてはならない）")

    # 人間関係
    relations: List[CharacterRelationSchema] = Field(default_factory=list)

class CharacterCreateRequest(AutoNovelBaseSchema):
    book_id: int
    name: str = Field(..., min_length=1, max_length=100)
    role: str = "sub"
    gender: str = ""
    age: str = ""
    appearance: str = ""
    personality: str = ""
    surface_persona: str = ""
    inner_conflict: str = ""
    core_trauma: str = ""
    save_the_cat_event: str = ""
    social_mask_vs_truth: str = ""
    iron_constraint: str = ""
    first_person: str = "私"
    second_person: str = "貴方"
    suffix_style: str = ""
    suffix_patterns: List[str] = Field(default_factory=list)
    dialogue_samples: List[str] = Field(default_factory=list)
    known_facts: List[str] = Field(default_factory=list)
    unknown_facts: List[str] = Field(default_factory=list)
    relations: List[CharacterRelationSchema] = Field(default_factory=list)
