from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS


class CharacterContext(BaseModel):
    """キャラクター外見・口調・性格・秘密設定の統合コンテキスト"""

    name: str = Field(default="", description="キャラクター名")
    role: str = Field(default="", description="役割・立ち位置")
    gender: str = Field(default="", description="性別")
    age: str = Field(default="", description="年齢")
    appearance: str = Field(default="", description="外見描写")
    visual_tags: List[str] = Field(default_factory=list, description="画像生成用外見タグ")
    personality: str = Field(default="", description="性格")
    surface_persona: str = Field(default="", description="表向きの社会的仮面")
    inner_conflict: str = Field(default="", description="内なる葛藤")
    iron_constraint: str = Field(default="", description="鉄の掟・行動原理")
    tone: str = Field(default="", description="口調・話し方")
    first_person: str = Field(default="私", description="一人称")
    second_person: str = Field(default="貴方", description="二人称")
    suffix_style: str = Field(default="", description="特徴的な語尾")
    social_mask_vs_truth: str = Field(default="", description="表の顔と裏の真実")
    known_facts: List[str] = Field(default_factory=list, description="知っている真実")
    unknown_facts: List[str] = Field(default_factory=list, description="知らない真実")
    secrets: List[str] = Field(default_factory=list, description="隠された秘密")

    model_config = MODEL_CONFIG_DEFAULTS

    def to_appearance_prompt(self) -> str:
        """画像生成用の外見プロンプト文字列を構築"""
        parts = []
        if self.gender:
            parts.append(f"{self.gender}")
        if self.age:
            parts.append(f"{self.age}")
        if self.appearance:
            parts.append(self.appearance)
        if self.visual_tags:
            parts.extend(self.visual_tags)
        return ", ".join(parts) if parts else self.name


class WorldContext(BaseModel):
    """世界観・用語・基本法則の統合コンテキスト"""

    title: str = Field(default="", description="作品タイトル")
    genre: str = Field(default="", description="ジャンル")
    concept: str = Field(default="", description="作品コンセプト")
    rules: List[str] = Field(default_factory=list, description="世界法則リスト")
    terminology: Dict[str, str] = Field(default_factory=dict, description="用語集")
    atmosphere: str = Field(default="", description="雰囲気・トーン")

    model_config = MODEL_CONFIG_DEFAULTS


class BibleContext(BaseModel):
    """全エージェント横断で共有される統合バイブル・コンテキスト"""

    book_id: Optional[int] = Field(default=None, description="作品ID")
    title: str = Field(default="", description="タイトル")
    genre: str = Field(default="", description="ジャンル")
    concept: str = Field(default="", description="コンセプト")
    mc: Optional[CharacterContext] = Field(default=None, description="主人公コンテキスト")
    characters: Dict[str, CharacterContext] = Field(
        default_factory=dict, description="キャラクター名/IDをキーとするコンテキスト辞書"
    )
    world: WorldContext = Field(default_factory=WorldContext, description="世界観コンテキスト")

    model_config = MODEL_CONFIG_DEFAULTS

    def get_character(self, name_or_id: str) -> Optional[CharacterContext]:
        """キャラクター名またはキーからコンテキストを検索"""
        if self.mc and (self.mc.name == name_or_id or name_or_id.lower() in ("mc", "hero", "protagonist")):
            return self.mc
        if name_or_id in self.characters:
            return self.characters[name_or_id]
        for name, char in self.characters.items():
            if name == name_or_id or char.name == name_or_id:
                return char
        return None

    def get_character_appearance_prompt(self, name_or_id: str) -> str:
        """指定キャラクターの画像生成用外見プロンプトを取得"""
        char = self.get_character(name_or_id)
        if char:
            return char.to_appearance_prompt()
        return ""
