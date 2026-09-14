"""挿絵付き商用EPUBの配信パック・DB自動引き当て統合テスト (Part 4: Step 45, 48)。"""

import io
import json
import zipfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import Book, Bible, Chapter
from src.backend.database.series_loader import SeriesDataLoader
from src.backend.multimedia_service import MultimediaService
from src.services.exporters.epub_manifest_builder import detect_image_media_type


# 1x1 ダミー画像バイナリ
DUMMY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=@0821\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
DUMMY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
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
        conn.commit()
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session_factory(db_engine):
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
        output_dir=tmp_path / "mm_bundle",
        series_loader=loader,
    )


def test_detect_image_media_type():
    """Step 44: 画像メディアタイプの判定検証。"""
    assert detect_image_media_type("test.jpg", DUMMY_JPEG) == "image/jpeg"
    assert detect_image_media_type("test.png", DUMMY_PNG) == "image/png"
    assert detect_image_media_type("test.webp", b"RIFF....WEBP") == "image/webp"
    assert detect_image_media_type("unknown.jpg") == "image/jpeg"


def test_export_ebook_with_db_illustrations(service, db_session, tmp_path):
    """Step 45: DBに保存されたイラストアセットを引き当ててEPUBに統合するテスト。"""
    # 1. 書籍 & チャプター作成
    book = Book(title="挿絵付き魔法小説", genre="ハイファンタジー (R15)", concept="魔法使いの弟子")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    for i in range(1, 3):
        chap = Chapter(
            book_id=book.id,
            branch_id=1,
            ep_num=i,
            title=f"第{i}章 魔法の始まり",
            content=f"第{i}章の本文。少年は杖を振った。",
            score_story=85,
        )
        db_session.add(chap)
    db_session.commit()

    # 2. 画像ファイルを一時ディレクトリに書き出し
    img_dir = tmp_path / "test_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path1 = img_dir / "front.jpg"
    img_path1.write_bytes(DUMMY_JPEG)
    img_path2 = img_dir / "chap2_insert.png"
    img_path2.write_bytes(DUMMY_PNG)

    # 3. multimedia_artifacts に挿絵レコードを挿入
    db_session.execute(
        text("""
            INSERT INTO multimedia_artifacts (book_id, asset_type, format, file_path, metadata_json, created_at)
            VALUES (:book_id, 'illustration', 'jpg', :path, :meta, CURRENT_TIMESTAMP)
        """),
        {
            "book_id": book.id,
            "path": str(img_path1),
            "meta": json.dumps({"position": "frontmatter", "caption": "巻頭カラー口絵", "media_type": "image/jpeg"}),
        },
    )
    db_session.execute(
        text("""
            INSERT INTO multimedia_artifacts (book_id, asset_type, format, file_path, metadata_json, created_at)
            VALUES (:book_id, 'illustration', 'png', :path, :meta, CURRENT_TIMESTAMP)
        """),
        {
            "book_id": book.id,
            "path": str(img_path2),
            "meta": json.dumps({"position": "chapter_start", "chapter_index": 2, "caption": "第2章 挿絵", "media_type": "image/png"}),
        },
    )
    db_session.commit()

    # 4. export_ebook 実行
    result = service.export_ebook(book_id=book.id, formats=["epub"])
    assert result.asset_id is not None
    assert result.metadata.get("illustration_count") == 2
    assert len(result.files) > 0

    # 5. 生成されたEPUBファイルを解凍・検証
    epub_file = Path(result.files[0])
    assert epub_file.exists()
    assert epub_file.suffix == ".epub"

    with zipfile.ZipFile(epub_file, "r") as zf:
        namelist = zf.namelist()
        # 挿絵画像とXHTMLが含まれること
        assert "item/images/front.jpg" in namelist
        assert "item/images/chap2_insert.png" in namelist
        # standard.opf の Spine 順序検証
        opf = zf.read("item/standard.opf").decode("utf-8")
        assert "p-ill-art_" in opf
        assert "img-art_" in opf


def test_export_ebook_skips_missing_image_file(service, db_session):
    """Step 40: 画像ファイルが存在しない場合もクラッシュせずスキップされること。"""
    book = Book(title="画像欠落テスト本", genre="ハイファンタジー (R15)", concept="テスト")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    chap = Chapter(book_id=book.id, branch_id=1, ep_num=1, title="第1章", content="本文", score_story=80)
    db_session.add(chap)
    db_session.commit()

    # 存在しないファイルパスを登録
    db_session.execute(
        text("""
            INSERT INTO multimedia_artifacts (book_id, asset_type, format, file_path, metadata_json, created_at)
            VALUES (:book_id, 'illustration', 'jpg', 'C:/non_existent_path/fake.jpg', '{}', CURRENT_TIMESTAMP)
        """),
        {"book_id": book.id},
    )
    db_session.commit()

    # エラーにならず出力されること
    result = service.export_ebook(book_id=book.id, formats=["epub"])
    assert result.asset_id is not None
    epub_file = Path(result.files[0])
    assert epub_file.exists()
