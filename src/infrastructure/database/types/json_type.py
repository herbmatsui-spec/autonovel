"""SQLiteとPostgreSQLを透過的に吸収するJSON型デコレータ。"""
from __future__ import annotations
import json
from typing import Any
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class CompatibleJSON(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return value
