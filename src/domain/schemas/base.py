from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AutoNovelBaseSchema(BaseModel):
    """v5.0 ドメインモデル共通基底クラス"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

class TimestampedSchema(AutoNovelBaseSchema):
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
