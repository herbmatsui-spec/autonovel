"""tests/e2e/test_v5_storage_parity.py - SQLite / PostgreSQL ストレージ等価性リグレッション防止テスト.

Alembic および SQLAlchemy の DDL / ORM モデルが
ローカル (SQLite) と本番 (PostgreSQL) の双方のダイアレクトに対して
型互換かつエラーなくコンパイル・適用できることを検証する。
"""

from __future__ import annotations

import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from src.infrastructure.database.models.base_orm import Base
import src.backend.database.models  # noqa: F401
import src.backend.database.models_tenant  # noqa: F401
import src.backend.database.models_billing  # noqa: F401


def test_sqlite_and_postgres_ddl_compilation_parity():
    """全モデルの DDL が SQLite と PostgreSQL の双方で正常にコンパイルできること."""
    sqlite_dialect = sqlite.dialect()
    pg_dialect = postgresql.dialect()

    tables = list(Base.metadata.tables.values())
    assert len(tables) > 10, "主要テーブルが10以上定義されていること"

    # 検証すべき必須テーブル群
    essential_tables = {
        "books",
        "chapters",
        "characters",
        "plots",
        "foreshadowing",
        "users",
        "internal_state",
    }
    table_names = set(Base.metadata.tables.keys())
    for name in essential_tables:
        assert name in table_names, f"必須テーブル '{name}' が Base.metadata に存在すること"

    for table in tables:
        # SQLite 向け DDL コンパイル
        create_sqlite = CreateTable(table).compile(dialect=sqlite_dialect)
        sqlite_ddl = str(create_sqlite)
        assert len(sqlite_ddl) > 0, f"Table {table.name} failed to compile for SQLite"

        # PostgreSQL 向け DDL コンパイル
        create_pg = CreateTable(table).compile(dialect=pg_dialect)
        pg_ddl = str(create_pg)
        assert len(pg_ddl) > 0, f"Table {table.name} failed to compile for PostgreSQL"


def test_compatible_types_column_parity():
    """CompatibleJSON, CompatibleDateTime 等の互換型カラムが両環境で妥当な型名を出力すること."""
    pg_dialect = postgresql.dialect()
    sqlite_dialect = sqlite.dialect()

    books_table = Base.metadata.tables["books"]
    ai_config_col = books_table.columns["ai_assistant_config"]
    created_at_col = books_table.columns["created_at"]

    # PostgreSQL では JSONB または JSON / TIMESTAMP
    pg_type_json = ai_config_col.type.compile(dialect=pg_dialect)
    assert "JSON" in pg_type_json.upper()

    pg_type_dt = created_at_col.type.compile(dialect=pg_dialect)
    assert any(token in pg_type_dt.upper() for token in ["TIMESTAMP", "DATETIME"])

    # SQLite では TEXT または JSON / DATETIME
    sqlite_type_json = ai_config_col.type.compile(dialect=sqlite_dialect)
    assert any(token in sqlite_type_json.upper() for token in ["JSON", "TEXT"])
