"""エクスポートパッケージ生成の統合テスト。

Step 18: book_data is None のフォールバック ZIP 検証
Step 27: real_db_manager フィクスチャ併用でのエージェント呼び出し
Step 47: real DB データ注入時の ZIP 内容検証
"""

from __future__ import annotations

import io
import json
import time
import zipfile

import pytest

from src.backend.database.repository import BookRepository
from src.models.book import Bible, Book, Chapter, Character, Plot
from src.services.marketing import MarketingAgent


@pytest.mark.asyncio
async def test_create_export_package_structure() -> None:
    """create_export_package が正常にZIPアーカイブを構築し、4ファイルが含まれることを検証。"""
    agent = MarketingAgent()

    dummy_book_data = {
        "title": "魔王城の料理人 (R15)",
        "genre": "異世界ファンタジー",
        "chapters": [
            {
                "ep_num": 1,
                "title": "追放された宮廷料理人",
                "content": "勇者パーティを追い出された男は、魔王城の厨房で包丁を握る。（※R15: 怪物解体描写あり）",
            }
        ],
        "characters": [
            {
                "name": "ルーク",
                "role": "主人公",
                "personality": "マイペース",
                "ability": "神速包丁",
            }
        ],
        "plots": [
            {
                "ep_num": 1,
                "title": "追放された宮廷料理人",
                "one_line_summary": "魔王に料理の腕を買われる。",
            }
        ],
    }

    zip_bytes, zip_filename = await agent.create_export_package(
        book_id=101, book_data=dummy_book_data
    )

    assert zip_filename == "export_101.zip"
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        filenames = z.namelist()
        assert "01_本文.txt" in filenames
        assert "02_キャラクター・世界観設定集.txt" in filenames
        assert "03_プロット概要.txt" in filenames
        assert "04_データダンプ.json" in filenames

        content_txt = z.read("01_本文.txt").decode("utf-8")
        assert "魔王城の料理人" in content_txt
        assert "追放された宮廷料理人" in content_txt

        # 04_データダンプ.json は有効 JSON かつ book_id を含む
        dump = json.loads(z.read("04_データダンプ.json").decode("utf-8"))
        assert dump["book_id"] == 101


@pytest.mark.asyncio
async def test_fallback_when_book_data_is_none() -> None:
    """Step 18: book_data 未指定時に DEFAULT_FALLBACK で ZIP が生成されることを検証。"""
    agent = MarketingAgent()
    fallback_bytes, fallback_filename = await agent.create_export_package(book_id=999)

    assert fallback_filename == "export_999.zip"
    assert len(fallback_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(fallback_bytes), "r") as zf:
        names = zf.namelist()
        assert "01_本文.txt" in names
        assert "04_データダンプ.json" in names
        content = zf.read("01_本文.txt").decode("utf-8")
        # DEFAULT_FALLBACK の title を含むこと
        from src.services.marketing import DEFAULT_FALLBACK

        assert DEFAULT_FALLBACK["title"] in content


@pytest.mark.asyncio
async def test_real_db_export_package_via_fixture(real_db_manager) -> None:
    """Step 27 & 47: real_db_manager フィクスチャ上で Book/Chapter 等を登録し、
    repo から取得した ZIP 内容を検証する。"""
    session = real_db_manager

    # テスト用 Book と関連データを直接 ORM で挿入
    book = Book(
        title="DB統合テスト小説",
        genre="SF",
        current_branch_id=1,
    )
    session.add(book)
    session.flush()  # book.id を確定
    book_id = book.id

    chapter = Chapter(
        book_id=book_id,
        ep_num=1,
        title="起動シークエンス",
        content="AI は目覚めた。",
        is_anchor=False,
    )
    character = Character(
        book_id=book_id,
        name="エイダ",
        role="主人公",
        personality="冷静",
        ability="論理掌握",
    )
    plot = Plot(
        book_id=book_id,
        branch_id=1,
        ep_num=1,
        title="起動シークエンス",
        one_line_summary="AI の覚醒。",
    )
    bible = Bible(
        book_id=book_id,
        settings=json.dumps({"world": "2099年の人類とAI"}, ensure_ascii=False),
        created_at=int(time.time()),
    )
    session.add_all([chapter, character, plot, bible])
    session.commit()

    # BookRepository 経由で export
    repo = BookRepository(session)
    agent = MarketingAgent(repo=repo)
    zip_bytes, zip_filename = await agent.create_export_package(book_id=book_id)

    assert zip_filename == f"export_{book_id}.zip"
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        assert "01_本文.txt" in names
        assert "02_キャラクター・世界観設定集.txt" in names
        assert "03_プロット概要.txt" in names
        assert "04_データダンプ.json" in names

        # real DB のデータが ZIP に反映されていることを検証
        body = zf.read("01_本文.txt").decode("utf-8")
        assert "DB統合テスト小説" in body
        assert "起動シークエンス" in body
        assert "AI は目覚めた。" in body

        chars = zf.read("02_キャラクター・世界観設定集.txt").decode("utf-8")
        assert "エイダ" in chars
        assert "論理掌握" in chars

        dump = json.loads(zf.read("04_データダンプ.json").decode("utf-8"))
        assert dump["book_id"] == book_id
        assert dump["title"] == "DB統合テスト小説"
        assert len(dump["chapters"]) == 1
        assert dump["chapters"][0]["title"] == "起動シークエンス"
