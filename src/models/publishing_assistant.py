from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS

class TargetPlatform(str, Enum):
    KAKUYOMU = "kakuyomu"
    NAROU = "narou"
    ALPHAPOLIS = "alphapolis"
    KINDLE = "kindle"

class FormattedChapterPayload(BaseModel):
    platform: TargetPlatform
    chapter_title: str = Field(..., description="章・話のタイトル")
    foreword: str = Field("", description="前書き（前話のおさらい等）")
    main_content: str = Field(..., description="プラットフォーム記法適用済み本文")
    afterword: str = Field("", description="後書き（AI利用明記、次回予告）")
    char_count: int = Field(0, description="本文・前書き・後書き総文字数または本文文字数")
    ai_disclosure_statement: str = Field("", description="AI利用開示文言")
    validation_warnings: list[str] = Field(default_factory=list, description="規約やフォーマットに関する警告一覧")

    model_config = MODEL_CONFIG_DEFAULTS
