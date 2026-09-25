"""tests/unit/test_export_zip.py - ZIP納品パッケージ生成と文字コード検証."""

from __future__ import annotations

import io
import json
import zipfile
import pytest

from src.services.marketing.export_package import MarketingService


@pytest.mark.asyncio
async def test_create_export_package_encoding_and_structure():
    service = MarketingService(repo=None)

    custom_data = {
        "title": "魔王を倒したあとのスローライフ",
        "genre": "ファンタジー (R15)",
        "chapters": [
            {
                "ep_num": 1,
                "title": "勇者の引退",
                "content": "平和になった世界で、男は小さなパン屋を開いた。\n朝の光が厨房を照らす。",
            }
        ],
        "characters": [
            {
                "name": "レオン",
                "role": "元勇者・店主",
                "personality": "穏やか",
                "ability": "聖剣技（封印中）",
            }
        ],
        "plots": [
            {
                "ep_num": 1,
                "title": "勇者の引退",
                "one_line_summary": "戦いを終えた元勇者が平穏な日常を始める。",
            }
        ],
    }

    zip_bytes, filename = await service.create_export_package(book_id=999, book_data=custom_data)

    assert filename == "export_999.zip"
    assert len(zip_bytes) > 0

    # ZIP 検証
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        assert "01_本文.txt" in names
        assert "02_キャラクター・世界観設定集.txt" in names
        assert "03_プロット概要.txt" in names
        assert "04_データダンプ.json" in names

        # 01_本文.txt: UTF-8 BOM (b"\xef\xbb\xbf") + CRLF チェック
        honbun_bytes = z.read("01_本文.txt")
        assert honbun_bytes.startswith(b"\xef\xbb\xbf")
        honbun_str = honbun_bytes.decode("utf-8-sig")
        assert "魔王を倒したあとのスローライフ" in honbun_str
        assert "\r\n" in honbun_str

        # 02: キャラクター設定集
        setting_bytes = z.read("02_キャラクター・世界観設定集.txt")
        assert setting_bytes.startswith(b"\xef\xbb\xbf")
        setting_str = setting_bytes.decode("utf-8-sig")
        assert "レオン" in setting_str

        # 04: JSON ダンプ
        dump_bytes = z.read("04_データダンプ.json")
        dump_data = json.loads(dump_bytes.decode("utf-8"))
        assert dump_data["book_id"] == 999
        assert dump_data["title"] == "魔王を倒したあとのスローライフ"
