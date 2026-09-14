"""実DBデータを用いた MultimediaService の結合テスト (Part 2: Step 22, 23)。"""

import json
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import Book, Bible, Chapter
from src.backend.database.series_loader import SeriesDataLoader
from src.backend.multimedia_service import MultimediaService
from src.backend.exceptions import NoChaptersFoundError
from fastapi.testclient import TestClient
from src.backend.server import app
from src.backend.routers.multimedia import get_multimedia_service


from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session_factory(db_engine):
    # DDL for SQLite tables needed by multimedia service
    from sqlalchemy import text
    with db_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS multimedia_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                asset_type TEXT,
                format TEXT,
                file_path TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS multimedia_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                asset_id INTEGER,
                status TEXT,
                error TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audio_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                episode_num INTEGER,
                file_path TEXT,
                duration_seconds REAL,
                file_size_bytes INTEGER,
                created_at TIMESTAMP
            );
        """))
        conn.commit()

    return sessionmaker(bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def service(session_factory, tmp_path, monkeypatch):
    from src.backend.config import settings
    monkeypatch.setattr(settings, "ENABLE_MULTIMEDIA", True)
    loader = SeriesDataLoader(session_factory=session_factory)
    return MultimediaService(
        session_factory=session_factory,
        output_dir=tmp_path / "multimedia",
        series_loader=loader,
    )


def test_real_db_generate_media_mix_and_ebook(service, db_session):
    """Step 22: DBデータを用いたマルチメディア生成の結合テスト。"""
    # 1. 書籍データの作成
    book = Book(
        title="勇者タロウの真実",
        genre="ハイファンタジー (R15)",
        concept="運命に抗う勇者の物語",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    bible = Bible(
        book_id=book.id,
        settings=json.dumps({
            "characters": {"archetypes": {"hero": "タロウ"}},
            "style": {"tone": "dramatic"},
        }),
    )
    db_session.add(bible)

    # 2. チャプター3話を作成
    for i in range(1, 4):
        chapter = Chapter(
            book_id=book.id,
            branch_id=1,
            ep_num=i,
            title=f"第{i}章 旅立ちの鐘",
            content=f"第{i}章の本文です。タロウは剣を抜いて魔王軍と対峙した。決意を胸に進む。",
            score_story=88,
        )
        db_session.add(chapter)
    db_session.commit()

    # 3. Media Mix (manga) 生成
    result_mm = service.generate_media_mix(book_id=book.id, format_name="manga", episode_num=1)
    assert result_mm.asset_id is not None
    assert len(result_mm.files) > 0
    # 生成ファイルの中身を確認
    first_file = Path(result_mm.files[0])
    assert first_file.exists()
    script_data = json.loads(first_file.read_text(encoding="utf-8"))
    assert "format" in script_data or "scenes" in script_data or "dialogues" in script_data or "title" in script_data

    # 4. Ebook (epub) 出力
    result_eb = service.export_ebook(book_id=book.id, formats=["epub"])
    assert result_eb.asset_id is not None
    assert len(result_eb.files) > 0
    epub_path = Path(result_eb.files[0])
    assert epub_path.exists()
    assert epub_path.stat().st_size > 0


def test_empty_book_raises_no_chapters_found(service, db_session):
    """Step 23: 章なし書籍に対するエラー発生検証。"""
    book = Book(
        title="空の本",
        genre="ハイファンタジー (R15)",
        concept="まだ何も書かれていない本",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    with pytest.raises(NoChaptersFoundError):
        service.generate_media_mix(book_id=book.id, format_name="manga")

    with pytest.raises(NoChaptersFoundError):
        service.export_ebook(book_id=book.id, formats=["epub"])


def test_empty_book_router_returns_422(service, db_session):
    """Step 23: 章なし書籍に対する FastAPI ルータの 422 応答検証。"""
    from src.backend.auth import validate_api_key_or_raise

    book = Book(
        title="空の本",
        genre="ハイファンタジー (R15)",
        concept="まだ何も書かれていない本",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    app.dependency_overrides[get_multimedia_service] = lambda: service
    app.dependency_overrides[validate_api_key_or_raise] = lambda: "valid_key"
    client = TestClient(app)

    try:
        response = client.post(
            "/multimedia/media-mix",
            json={"book_id": book.id, "format": "manga", "episode_num": 1},
            headers={"X-API-Key": "valid_key"},
        )
        # 422 Unprocessable Entity が返ることを確認
        assert response.status_code == 422
        detail = response.json().get("detail", "")
        assert f"No chapters found for book {book.id}" in detail
    finally:
        app.dependency_overrides.pop(get_multimedia_service, None)
        app.dependency_overrides.pop(validate_api_key_or_raise, None)
