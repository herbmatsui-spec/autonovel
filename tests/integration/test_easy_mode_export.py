import io
import zipfile
import pytest
from src.services.marketing import MarketingAgent


@pytest.mark.asyncio
async def test_create_export_package_structure():
    """create_export_package が正常にZIPアーカイブを構築し、指定された4ファイルが含まれることを検証"""
    agent = MarketingAgent()
    
    dummy_book_data = {
        "title": "魔王城の料理人 (R15)",
        "genre": "異世界ファンタジー",
        "chapters": [
            {
                "ep_num": 1,
                "title": "追放された宮廷料理人",
                "content": "勇者パーティを追い出された男は、魔王城の厨房で包丁を握る。（※R15: 怪物解体描写あり）"
            }
        ],
        "characters": [
            {"name": "ルーク", "role": "主人公", "personality": "マイペース", "ability": "神速包丁"}
        ],
        "plots": [
            {"ep_num": 1, "title": "追放された宮廷料理人", "one_line_summary": "魔王に料理の腕を買われる。"}
        ]
    }

    zip_bytes, zip_filename = await agent.create_export_package(book_id=101, book_data=dummy_book_data)

    assert zip_filename == "export_101.zip"
    assert len(zip_bytes) > 0

    # ZIPファイルの中身を解凍検証
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        filenames = z.namelist()
        assert "01_本文.txt" in filenames
        assert "02_キャラクター・世界観設定集.txt" in filenames
        assert "03_プロット概要.txt" in filenames
        assert "04_データダンプ.json" in filenames

        # 01_本文.txt の内容チェック
        content_txt = z.read("01_本文.txt").decode("utf-8")
        assert "魔王城の料理人" in content_txt
        assert "追放された宮廷料理人" in content_txt
