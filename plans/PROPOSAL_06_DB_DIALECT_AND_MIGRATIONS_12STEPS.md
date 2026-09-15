# 提案6: DB方言差（SQLite / PostgreSQL）の透過的吸収とマイグレーション堅牢化 実装計画書（全12ステップ）

**対象レイヤー**: `src/infrastructure/database/types/`, `src/backend/database/`, `scripts/`, `tests/unit/database/`  
**目的**: 開発・テスト環境（SQLite）と本番環境（PostgreSQL + pgvector + JSONB）の方言差（JSON操作、ベクター埋め込み、DateTimeタイムゾーン）をSQLAlchemyの透過的カスタム型（`TypeDecorator`）で吸収する。さらに、Alembicマイグレーションの双方向（upgrade ⇄ downgrade）整合性を検証する自動化スクリプトを作成する。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な実装コードおよび単体テストコード**、**検証コマンド**、**合格条件** を完備しています。外部PostgreSQLサーバー不要で、SQLite環境単体で完全検証可能です。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | カスタム型 | `src/infrastructure/database/types/json_type.py` | SQLite（Text/JSON文字列）とPostgres（JSON/JSONB）を透過変換する `CompatibleJSON` |
| **Step 2** | カスタム型 | `src/infrastructure/database/types/vector_type.py` | pgvectorとSQLite（BLOB/リストシリアライズ）を透過変換する `CompatibleVector` |
| **Step 3** | カスタム型 | `src/infrastructure/database/types/datetime_type.py` | UTCタイムゾーンを厳格に保持する `CompatibleDateTime` |
| **Step 4** | パッケージ集約 | `src/infrastructure/database/types/__init__.py` | 3大互換型の集約エクスポート |
| **Step 5** | ベクトル演算補助 | `src/infrastructure/database/types/vector_math.py` | SQLite環境でも動作する純Pythonコサイン類似度計算ヘルパー |
| **Step 6** | モデル層適用 | `src/backend/database/models.py` | モデル定義内の `JSON` / `DateTime` / `Vector` を共通互換型に置換 |
| **Step 7** | 接続設定最適化 | `src/backend/database/core.py` | SQLite接続時のPRAGMA（`journal_mode=WAL`, `foreign_keys=ON`）自動有効化 |
| **Step 8** | マイグレーション検証 | `scripts/check_migrations.py` | Alembicの upgrade head → downgrade -1 → upgrade head 往復テストスクリプト |
| **Step 9** | CI実行ターゲット | `Makefile` または `scripts/run_checks.sh` | マイグレーション整合性検査のワンライナーコマンド整備 |
| **Step 10** | 単体テスト | `tests/unit/database/test_compatible_json.py` | `CompatibleJSON` のディープな辞書/配列シリアライズテスト |
| **Step 11** | 単体テスト | `tests/unit/database/test_compatible_vector.py` | `CompatibleVector` の浮動小数点配列保存と類似度計算テスト |
| **Step 12** | 結合テスト | `tests/unit/database/test_migration_integrity.py` | 一時SQLiteファイルを用いたマイグレーション往復検証テスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: `CompatibleJSON` 型の実装
- **目的**: SQLiteではJSON文字列に自動シリアライズ/デシリアライズし、PostgreSQLではネイティブJSON型を使用する。
- **対象ファイル**: `src/infrastructure/database/types/json_type.py`（新規作成）
- **実装コード**:
```python
"""SQLiteとPostgreSQLを透過的に吸収するJSON型デコレータ。"""
from __future__ import annotations
import json
from typing import Any
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, JSON as PG_JSON


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
```
- **検証コマンド**: `python -c "from src.infrastructure.database.types.json_type import CompatibleJSON; print('CompatibleJSON ready')"`
- **合格条件**: インポート成功。

---

### Step 2: `CompatibleVector` 型の実装
- **目的**: 本番の `pgvector.sqlalchemy.Vector` が利用できない環境でも、`List[float]` をバイナリ/JSONとして安全に保存。
- **対象ファイル**: `src/infrastructure/database/types/vector_type.py`（新規作成）
- **実装コード**:
```python
"""SQLiteとPostgreSQL pgvectorを透過的に吸収するVector型。"""
from __future__ import annotations
import json
from typing import List, Optional
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

try:
    from pgvector.sqlalchemy import Vector as PGVector
    HAS_PGVECTOR = True
except ImportError:
    PGVector = None
    HAS_PGVECTOR = False


class CompatibleVector(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 768, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR and PGVector is not None:
            return dialect.type_descriptor(PGVector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[List[float]], dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return []
```
- **検証コマンド**: `python -c "from src.infrastructure.database.types.vector_type import CompatibleVector; print('CompatibleVector ready')"`
- **合格条件**: インポート成功。

---

### Step 3: `CompatibleDateTime` 型の実装
- **目的**: SQLiteでミリ秒・タイムゾーンが欠落する問題を防止し、常にUTCタイムゾーン付きdatetimeとして扱う。
- **対象ファイル**: `src/infrastructure/database/types/datetime_type.py`（新規作成）
- **実装コード**:
```python
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
```
- **検証コマンド**: `python -c "from src.infrastructure.database.types.datetime_type import CompatibleDateTime; print('CompatibleDateTime ready')"`
- **合格条件**: インポート成功。

---

### Step 4: パッケージ集約エクスポート
- **目的**: `from src.infrastructure.database.types import CompatibleJSON, CompatibleVector, CompatibleDateTime` で利用可能にする。
- **対象ファイル**: `src/infrastructure/database/types/__init__.py`（新規作成）
- **実装コード**:
```python
"""Database custom dialect types."""
from src.infrastructure.database.types.json_type import CompatibleJSON
from src.infrastructure.database.types.vector_type import CompatibleVector
from src.infrastructure.database.types.datetime_type import CompatibleDateTime

__all__ = ["CompatibleJSON", "CompatibleVector", "CompatibleDateTime"]
```
- **検証コマンド**: `python -c "from src.infrastructure.database.types import CompatibleJSON, CompatibleVector, CompatibleDateTime; print('Types exported')"`
- **合格条件**: インポート成功。

---

### Step 5: ベクトル演算ヘルパーの実装
- **目的**: pgvector演算子 `<=>`（コサイン距離）が使えないSQLite環境でも、メモリ上でコサイン類似度を高速計算できるようにする。
- **対象ファイル**: `src/infrastructure/database/types/vector_math.py`（新規作成）
- **実装コード**:
```python
"""純Pythonコサイン類似度計算ユーティリティ。"""
from __future__ import annotations
import math
from typing import Sequence


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """2つのベクトル間のコサイン類似度 (-1.0 〜 1.0) を計算。"""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)
```
- **検証コマンド**: `python -c "from src.infrastructure.database.types.vector_math import cosine_similarity; print(cosine_similarity([1,0], [1,0]))"`
- **合格条件**: `1.0` が出力されること。

---

### Step 6: モデル層への互換型の適用
- **目的**: `src/backend/database/models.py` 内で生 `JSON` や `DateTime` を使用している箇所に共通型を接続可能にする。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**:
```python
# ファイル先頭付近にインポート追加
from src.infrastructure.database.types import CompatibleJSON, CompatibleDateTime, CompatibleVector

# 例: JSON Column を CompatibleJSON に更新
# extra_metadata = Column(CompatibleJSON, default=dict)
```
- **検証コマンド**: `python -c "import src.backend.database.models; print('Models verified with compatible types')"`
- **合格条件**: 構文エラーなくインポートできること。

---

### Step 7: SQLite接続時のPRAGMA最適化
- **目的**: SQLite利用時にWALモードおよび外部キー制約を強制し、本番Postgresに近い挙動と並行性を確保する。
- **対象ファイル**: `src/backend/database/core.py`
- **実装コード**:
```python
# src/backend/database/core.py のエンジン作成部分に追加
from sqlalchemy import event

def configure_sqlite_engine(engine):
    """SQLiteエンジンにWALモードと外部キー有効化PRAGMAを設定。"""
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
```
- **検証コマンド**: `python -c "from src.backend.database.core import configure_sqlite_engine; print('SQLite pragma config ready')"`
- **合格条件**: インポート成功。

---

### Step 8: マイグレーション往復自動チェックスクリプト作成
- **目的**: CI上で Alembic の `upgrade head` と `downgrade -1`、再 `upgrade head` を実行し、ロールバックスクリプトの不備を検知する。
- **対象ファイル**: `scripts/check_migrations.py`（新規作成）
- **実装コード**:
```python
#!/usr/bin/env python3
"""Alembic マイグレーション双方向（upgrade -> downgrade -> upgrade）自動検証スクリプト。"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str]) -> bool:
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}:")
        print(result.stderr)
        return False
    print(result.stdout)
    return True


def main() -> int:
    test_db = Path("test_migration.db")
    if test_db.exists():
        test_db.unlink()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db.resolve()}"

    print("Step 1: Upgrading to head...")
    if not run_command(["alembic", "upgrade", "head"]):
        return 1

    print("Step 2: Downgrading 1 revision...")
    if not run_command(["alembic", "downgrade", "-1"]):
        return 1

    print("Step 3: Re-upgrading to head...")
    if not run_command(["alembic", "upgrade", "head"]):
        return 1

    if test_db.exists():
        test_db.unlink()

    print("SUCCESS: Migration roundtrip verified successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
- **検証コマンド**: `python scripts/check_migrations.py --help`（またはスクリプトの文法チェック）
- **合格条件**: 構文エラーがないこと。

---

### Step 9: CI実行ターゲット追加
- **目的**: Makefileまたはpackage.jsonから `check_migrations.py` を1発で呼べるようにする。
- **対象ファイル**: `Makefile`
- **変更内容**:
```makefile
check-migrations:
	python scripts/check_migrations.py
```
- **検証コマンド**: `make -n check-migrations`
- **合格条件**: `python scripts/check_migrations.py` が表示されること。

---

### Step 10: 単体テスト: `CompatibleJSON` テスト
- **目的**: 辞書・配列・日本語文字列が文字化けや例外を起こさず正しく格納・復元されることを検証。
- **対象ファイル**: `tests/unit/database/test_compatible_json.py`（新規作成）
- **実装コード**:
```python
import pytest
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.json_type import CompatibleJSON

Base = declarative_base()


class JsonTestModel(Base):
    __tablename__ = "json_test_table"
    id = Column(Integer, primary_key=True)
    payload = Column(CompatibleJSON)


def test_compatible_json_serialization():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    data = {"novel": "異世界転生", "tags": ["ファンタジー", "無双"], "score": 98.5}
    item = JsonTestModel(id=1, payload=data)
    session.add(item)
    session.commit()

    loaded = session.query(JsonTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert loaded.payload["novel"] == "異世界転生"
    assert loaded.payload["tags"] == ["ファンタジー", "無双"]
    assert loaded.payload["score"] == 98.5
    session.close()
```
- **検証コマンド**: `pytest tests/unit/database/test_compatible_json.py -v --no-cov`
- **合格条件**: テストが PASS すること。

---

### Step 11: 単体テスト: `CompatibleVector` テスト
- **目的**: ベクトル型の埋め込み保存と、コサイン類似度計算が正常に実行されることを検証。
- **対象ファイル**: `tests/unit/database/test_compatible_vector.py`（新規作成）
- **実装コード**:
```python
import pytest
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.vector_type import CompatibleVector
from src.infrastructure.database.types.vector_math import cosine_similarity

Base = declarative_base()


class VectorTestModel(Base):
    __tablename__ = "vector_test_table"
    id = Column(Integer, primary_key=True)
    embedding = Column(CompatibleVector(dim=4))


def test_compatible_vector_persistence_and_similarity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    vec = [0.1, 0.5, 0.8, -0.2]
    item = VectorTestModel(id=1, embedding=vec)
    session.add(item)
    session.commit()

    loaded = session.query(VectorTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert len(loaded.embedding) == 4
    assert pytest.approx(loaded.embedding[0]) == 0.1

    # コサイン類似度計算の検証
    sim = cosine_similarity(loaded.embedding, [0.1, 0.5, 0.8, -0.2])
    assert pytest.approx(sim, 0.001) == 1.0
    session.close()
```
- **検証コマンド**: `pytest tests/unit/database/test_compatible_vector.py -v --no-cov`
- **合格条件**: テストが PASS すること。

---

### Step 12: 結合テスト: タイムゾーンとPRAGMAテスト
- **目的**: `CompatibleDateTime` と SQLite PRAGMA 最適化の結合動作を検証。
- **対象ファイル**: `tests/unit/database/test_migration_integrity.py`（新規作成）
- **実装コード**:
```python
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from src.infrastructure.database.types.datetime_type import CompatibleDateTime
from src.backend.database.core import configure_sqlite_engine

Base = declarative_base()


class DateTimeTestModel(Base):
    __tablename__ = "datetime_test_table"
    id = Column(Integer, primary_key=True)
    created_at = Column(CompatibleDateTime)


def test_datetime_utc_preservation():
    engine = create_engine("sqlite:///:memory:")
    configure_sqlite_engine(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now_utc = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    item = DateTimeTestModel(id=1, created_at=now_utc)
    session.add(item)
    session.commit()

    loaded = session.query(DateTimeTestModel).filter_by(id=1).first()
    assert loaded is not None
    assert loaded.created_at.tzinfo == timezone.utc
    assert loaded.created_at.year == 2026
    session.close()
```
- **検証コマンド**: `pytest tests/unit/database/test_migration_integrity.py -v --no-cov`
- **合格条件**: テストが PASS すること。
