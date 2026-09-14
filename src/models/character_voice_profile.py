from __future__ import annotations
from pydantic import BaseModel, Field

class CharacterVoiceProfile(BaseModel):
    character_name: str
    first_person: list[str] = Field(..., description="一人称 (例: ['俺', 'オレ'])")
    second_person: list[str] = Field(..., description="二人称 (例: ['お前', '貴様'])")
    endings: list[str] = Field(..., description="許可される語尾 (例: ['〜だぜ', '〜な'])")
    forbidden_words: list[str] = Field(default_factory=list, description="絶対に使わない語彙")
    catchphrases: list[str] = Field(default_factory=list, description="口癖・決め台詞")
    sample_dialogue: str = Field("", description="代表的なセリフ例")
