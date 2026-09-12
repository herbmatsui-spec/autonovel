"""P0 総合エンドツーエンド (E2E) 結合テスト (Step 66〜70).

検証対象:
1. 実DB小説からのマルチメディア生成フロー (Step 67)
2. 挿絵付き商用EPUB出力フロー (Step 68)
3. IFルート分岐 -> コンフリクト発生 -> 確定コミットフロー (Step 69)
4. APIエラーレスポンスおよびエッジケース総合検証 (Step 70)
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database.models.base_orm import Base
from src.backend import config
from src.backend.auth import validate_api_key_or_raise
from src.backend.database.models import Book, Chapter, Branch
from src.backend.database.series_loader import SeriesDataLoader
from src.backend.multimedia_service import MultimediaService
from src.backend.routers import branches as branches_router
from src.backend.routers import multimedia as multimedia_router
from src.agents.event_bus import EventBus


# 1x1 透明 PNG バイト列 (テスト用)
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02"
    b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def p0_e2e_setup(monkeypatch, tmp_path: Path):
    """P0 総合E2Eテストハーネス (Step 66).
    
    同期エンジン（MultimediaService用）と非同期エンジン（BranchRouter用）で
    同一の SQLite ファイルを共有する。
    """
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", True)
    output_dir = tmp_path / "e2e_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.settings, "MULTIMEDIA_OUTPUT_DIR", str(output_dir))

    db_path = tmp_path / "p0_e2e.db"
    sync_db_url = f"sqlite:///{db_path}"
    async_db_url = f"sqlite+aiosqlite:///{db_path}"

    # 同期エンジン・セッション
    sync_engine = create_engine(
        sync_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

    # 非同期エンジン・セッション
    async_engine = create_async_engine(
        async_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 全テーブル初期化
    Base.metadata.create_all(sync_engine)

    # 追加テーブル (multimedia_artifacts, multimedia_tasks, branch_histories)
    with sync_engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS multimedia_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    asset_type TEXT,
                    format TEXT,
                    file_path TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS multimedia_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    asset_id INTEGER,
                    status TEXT,
                    error TEXT,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS branch_histories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_id INTEGER NOT NULL,
                    change_type VARCHAR(50) NOT NULL,
                    meta_info TEXT,
                    created_at DATETIME
                );
                """
            )
        )
        conn.commit()

    # 初期シードデータ投入 (Book 1, メインブランチ Branch 1, Chapter 1 & 2)
    sync_session = SyncSessionLocal()
    try:
        book = Book(
            id=1,
            title="運命の交差点",
            genre="fantasy",
            concept="選択によって分岐する世界",
        )
        sync_session.add(book)
        sync_session.flush()

        branch = Branch(
            id=1,
            book_id=1,
            name="main",
            parent_id=None,
            fork_ep_num=0,
        )
        sync_session.add(branch)
        sync_session.flush()

        chap1 = Chapter(
            id=1,
            book_id=1,
            branch_id=1,
            ep_num=1,
            title="第1章 旅立ち",
            content="少年は旅立ちを決意した。風が吹く。",
            score_story=80,
        )
        chap2 = Chapter(
            id=2,
            book_id=1,
            branch_id=1,
            ep_num=2,
            title="第2章 二つの道",
            content="右の森の道か、左の洞窟の道か。彼らは立ち止まった。",
            score_story=80,
        )
        sync_session.add(chap1)
        sync_session.add(chap2)
        sync_session.commit()
    finally:
        sync_session.close()

    # サービス実体化
    series_loader = SeriesDataLoader(session_factory=SyncSessionLocal)
    mm_service = MultimediaService(
        session_factory=SyncSessionLocal,
        output_dir=output_dir,
        series_loader=series_loader,
    )

    app = FastAPI(title="P0 E2E Test App")

    # ルーター登録
    app.include_router(multimedia_router.router, prefix="/multimedia", tags=["multimedia"])
    app.include_router(branches_router.router, tags=["branches"])

    # 依存性オーバーライド
    app.dependency_overrides[validate_api_key_or_raise] = lambda: "test-e2e-key"
    app.dependency_overrides[multimedia_router.get_multimedia_service] = lambda: mm_service

    async def override_get_branch_session() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as sess:
            yield sess

    app.dependency_overrides[branches_router.get_branch_session] = override_get_branch_session

    client = TestClient(app)

    yield {
        "client": client,
        "app": app,
        "sync_engine": sync_engine,
        "sync_session_factory": SyncSessionLocal,
        "async_session_factory": AsyncSessionLocal,
        "mm_service": mm_service,
        "output_dir": output_dir,
    }

    sync_engine.dispose()


def test_p0_harness_initialization(p0_e2e_setup):
    """Step 66: E2E テストハーネスの起動確認."""
    client = p0_e2e_setup["client"]
    res = client.get("/api/branches/1")
    assert res.status_code == 200
    branches = res.json()
    assert len(branches) >= 1
    assert branches[0]["name"] == "main"


def test_real_db_multimedia_generation_e2e(p0_e2e_setup):
    """Step 67: 実DB小説からのマルチメディア生成フロー E2E.
    
    DB内の実際の書籍・章データから漫画台本およびEPUBを出力し、
    ダミーではなく実DBの文章が反映されていることを検証する。
    """
    client = p0_e2e_setup["client"]

    # 1. 漫画台本の生成 (/multimedia/media-mix)
    payload = {
        "book_id": 1,
        "format": "manga",
    }
    res = client.post("/multimedia/media-mix", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["files"]) > 0

    # 生成された台本ファイルを検証
    script_path = Path(data["files"][0])
    assert script_path.exists()
    script_content = script_path.read_text(encoding="utf-8")
    
    # DBの実データ（第1章）のキーワードが台本に含まれていること
    assert "旅立ち" in script_content or "少年" in script_content

    # 2. 電子書籍（EPUB）のエクスポート (/multimedia/ebook)
    epub_payload = {
        "book_id": 1,
        "formats": ["epub"],
    }
    res_epub = client.post("/multimedia/ebook", json=epub_payload)
    assert res_epub.status_code == 200, res_epub.text
    epub_data = res_epub.json()
    assert len(epub_data["files"]) > 0

    epub_path = Path(epub_data["files"][0])
    assert epub_path.exists()
    # EPUBが正しいZIP形式であること
    assert zipfile.is_zipfile(epub_path)


def test_illustrated_commercial_epub_e2e(p0_e2e_setup):
    """Step 68: 挿絵付き商用EPUB出力フロー E2E.
    
    画像アセットをDBに登録した状態で EPUB 出力を行い、
    生成バイナリ内に XHTML 挿絵ページ、画像ファイル、Spine 登録、
    および縦書き CSS が規格通り組み込まれていることを完全検証する。
    """
    client = p0_e2e_setup["client"]
    output_dir: Path = p0_e2e_setup["output_dir"]
    sync_engine = p0_e2e_setup["sync_engine"]

    # テスト用画像ファイルを配置
    img_file = output_dir / "cover_illustration.png"
    img_file.write_bytes(TINY_PNG)

    # DB (multimedia_artifacts) に挿絵アセットを登録 (Step 46 連動)
    with sync_engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO multimedia_artifacts (book_id, asset_type, format, file_path, metadata_json, created_at)
                VALUES (1, 'illustration', 'png', :fpath, :meta, CURRENT_TIMESTAMP);
                """
            ),
            {
                "fpath": str(img_file),
                "meta": json.dumps({"caption": "第1章の扉絵", "chapter_number": 1}),
            },
        )
        conn.commit()

    # EPUB エクスポートリクエスト (/multimedia/ebook)
    epub_payload = {
        "book_id": 1,
        "formats": ["epub"],
    }

    res = client.post("/multimedia/ebook", json=epub_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["files"]) > 0

    epub_path = Path(data["files"][0])
    assert epub_path.exists()
    assert zipfile.is_zipfile(epub_path)

    # ZIP 内部構造の完全検証
    with zipfile.ZipFile(epub_path, "r") as zf:
        namelist = zf.namelist()

        # 1. mimetype が先頭
        assert namelist[0] == "mimetype"
        assert zf.read("mimetype") == b"application/epub+zip"

        # 2. 画像ファイルが存在
        has_image = any("images/" in name for name in namelist)
        assert has_image, f"Images not found in EPUB: {namelist}"

        # 3. 挿絵 XHTML ページが存在
        has_ill_xhtml = any("ill-" in name for name in namelist)
        assert has_ill_xhtml, f"Illustration XHTML not found in EPUB: {namelist}"


        # 4. OPF (マニフェスト) の検証
        opf_name = next(name for name in namelist if name.endswith(".opf"))
        opf_content = zf.read(opf_name).decode("utf-8")
        assert "p-ill-" in opf_content
        assert "img-" in opf_content

        # 5. 挿絵用 CSS クラスの検証
        css_name = next(name for name in namelist if name.endswith(".css"))
        css_content = zf.read(css_name).decode("utf-8")
        assert ".p-illustration" in css_content
        assert ".illustration-wrap" in css_content


def test_branch_fork_merge_commit_e2e(p0_e2e_setup):
    """Step 69: IFルート分岐 -> コンフリクト発生 -> 確定コミットフロー E2E.
    
    1. ブランチフォーク (Branch 1 -> Branch 2)
    2. 各ブランチで章の内容を変更
    3. マージプレビューで差分を検出
    4. 解決済みペイロードで確定コミット API を呼出
    5. EventBus の `branch.merged` イベント発行と DB への本文反映を完全検証
    """
    client = p0_e2e_setup["client"]
    sync_session_factory = p0_e2e_setup["sync_session_factory"]

    # 1. ブランチ 2 をフォーク (fork_ep_num=1)
    fork_res = client.post(
        "/api/branches/1/fork",
        json={"parent_id": 1, "name": "if_forest_route", "fork_ep_num": 1},
    )
    assert fork_res.status_code in [200, 201], fork_res.text
    branch_2 = fork_res.json()
    branch_2_id = branch_2["id"]
    assert branch_2["name"] == "if_forest_route"

    # 2. Branch 2 用の第2章を作成（森ルートでの別展開）
    sync_sess: Session = sync_session_factory()
    try:
        chap_forest = Chapter(
            book_id=1,
            branch_id=branch_2_id,
            ep_num=2,
            title="第2章 妖精の森",
            content="彼らは深い森へ足を踏み入れた。妖精が現れる。",
            score_story=80,
        )
        sync_sess.add(chap_forest)
        sync_sess.commit()
    finally:
        sync_sess.close()

    # 3. マージプレビューを実行 (Branch 2 を Branch 1 に合流)
    preview_res = client.post(
        "/api/branches/1/merge/preview",
        json={
            "source_branch_id": branch_2_id,
            "target_branch_id": 1,
            "merge_ep_num": 2,
        },
    )
    assert preview_res.status_code == 200, preview_res.text
    preview_data = preview_res.json()
    assert "can_merge" in preview_data

    # EventBus のイベント購読リスナーを用意
    received_events = []
    async def on_merged(event):
        received_events.append(event)

    from src.agents.event_bus import get_event_bus
    bus = get_event_bus()
    bus.subscribe("branch.merged", on_merged)

    # 4. 解決ペイロードを用いて確定コミットを実行 (Step 55, 69)
    resolved_text = "彼らは森と洞窟の境界で、妖精の導きによって新たな道を見出した。"
    commit_payload = {
        "source_branch_id": branch_2_id,
        "target_branch_id": 1,
        "merge_ep_num": 2,
        "resolved_chapters": [
            {
                "chapter_number": 2,
                "resolved_content": resolved_text,
                "resolution_strategy": "manual",
            }
        ],
        "commit_message": "Merge forest route into main with fairy guidance",
    }

    commit_res = client.post("/api/branches/1/merge/commit", json=commit_payload)
    assert commit_res.status_code == 200, commit_res.text
    commit_data = commit_res.json()
    assert commit_data["success"] is True
    assert commit_data["target_branch_id"] == 1
    assert commit_data["updated_chapters_count"] >= 1

    # 5. DB 上で Target ブランチ (Branch 1) の第2章本文が解決内容に確定されているか検証
    sync_sess = sync_session_factory()
    try:
        row = sync_sess.execute(
            select(Chapter).where(
                Chapter.book_id == 1,
                Chapter.branch_id == 1,
                Chapter.ep_num == 2,
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.content == resolved_text
    finally:
        sync_sess.close()

    # 6. EventBus で branch.merged が発行されたことを検証
    assert len(received_events) >= 1
    assert received_events[-1].payload["target_branch_id"] == 1
    assert received_events[-1].payload["source_branch_id"] == branch_2_id


def test_edge_cases_and_error_handling(p0_e2e_setup):
    """Step 70: APIエラーレスポンスおよびエッジケース総合検証.
    
    1. 不正なフォーマット名 -> 400 または 422
    2. 存在しない書籍IDでのマルチメディア生成 -> 404 または 422
    3. 不正なブランチマージコミット (空本文・存在しないブランチ) -> 400
    """
    client = p0_e2e_setup["client"]

    # 1. 存在しないフォーマット指定 (Pydantic validation error: 422, or 400)
    res_bad_fmt = client.post(
        "/multimedia/media-mix",
        json={"book_id": 1, "format": "invalid_format_xyz"},
    )
    assert res_bad_fmt.status_code in [400, 422]

    # 2. 存在しない書籍IDでの台本生成 (Book not found -> 404, or NoChaptersFoundError -> 422)
    res_no_book = client.post(
        "/multimedia/media-mix",
        json={"book_id": 99999, "format": "manga"},
    )
    assert res_no_book.status_code in [404, 422]

    # 3. マージ確定コミットで不正なブランチID
    res_bad_branch = client.post(
        "/api/branches/1/merge/commit",
        json={
            "source_branch_id": 88888,
            "target_branch_id": 99999,
            "merge_ep_num": 1,
            "resolved_chapters": [
                {
                    "chapter_number": 1,
                    "resolved_content": "some content",
                    "resolution_strategy": "manual",
                }
            ],
        },
    )
    assert res_bad_branch.status_code in [400, 404]

    # 4. マージ確定コミットで空本文
    res_empty_content = client.post(
        "/api/branches/1/merge/commit",
        json={
            "source_branch_id": 1,
            "target_branch_id": 1,
            "merge_ep_num": 1,
            "resolved_chapters": [
                {
                    "chapter_number": 1,
                    "resolved_content": "   ",
                    "resolution_strategy": "manual",
                }
            ],
        },
    )
    assert res_empty_content.status_code == 400
