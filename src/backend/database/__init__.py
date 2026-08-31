"""SQLAlchemy engine と SessionLocal を初期化するデータベース設定モジュール。"""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.backend.config import settings
from src.models import Base

# settings から DATABASE_URL を取得
DATABASE_URL = settings.DATABASE_URL

# SQLite の場合は check_same_thread=False が必要
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依存注入用の DB セッションジェネレーター"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """データベースのテーブルを初期化する"""
    Base.metadata.create_all(bind=engine)


__all__: list[str] = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
]
