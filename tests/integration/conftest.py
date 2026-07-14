"""
tests/integration/conftest.py
統合テスト用の共有フィクスチャ（SQLite + 実DBマネージャー）
"""
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from src.backend.database.core import DatabaseManager
from src.backend.database.models import Base
from src.backend.database.uow import UnitOfWork


@pytest.fixture
async def real_uow():
    """
    実際の SQLite データベースを用いた UnitOfWork を提供する。

    - 一時ファイルDBを作成し、最新スキーマを create_all で構築
    - コミットパスは ChromaDB へは同期せず Outbox テーブルに記録するため、
      ChromaDB が起動していなくても動作する
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # スキーマ構築（同期エンジン）
    sync_url = f"sqlite:///{db_path}"
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    manager = DatabaseManager(db_url)
    uow = UnitOfWork(db=manager)

    yield uow

    try:
        db_path.unlink()
    except OSError:
        pass


@pytest.fixture
def chroma_url():
    """CI環境の ChromaDB エンドポイント（docker-compose.ci.yml で 8000 番）"""
    import os

    return os.environ.get("CHROMA_URL", "http://localhost:8000")


@pytest.fixture
def mock_st_context():
    """Streamlit アプリ統合テスト用のコンテキストモック"""
    from tests.mocks.mock_streamlit import MockStreamlitContext

    return MockStreamlitContext()
