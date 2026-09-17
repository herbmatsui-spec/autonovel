"""常にUTCタイムゾーン付きとして安全に変換するDateTime型。"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class CompatibleDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            # タイムゾーンなしの場合はUTCとみなす
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
